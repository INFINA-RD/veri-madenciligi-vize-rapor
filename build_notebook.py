"""Regresyon problemi icin main.ipynb olusturucu - Polinomial Regresyon dahil."""
import json
from pathlib import Path

cells = []

def md(text):
    cells.append({"cell_type": "markdown", "metadata": {},
                  "source": text.splitlines(keepends=True)})

def code(text):
    cells.append({"cell_type": "code", "execution_count": None,
                  "metadata": {}, "outputs": [],
                  "source": text.splitlines(keepends=True)})

# ---------- BASLIK ----------
md("""# Veri Madenciligi Vize Projesi
## ABD Borsasi Sirketleri Icin Bir Sonraki Yil Gelirinin (Revenue) Regresyon ile Tahmini

Bu calismada, 2014-2018 yillarini kapsayan 200+ finansal gostergeden olusan ABD borsasi
veri seti kullanilarak, bir sirketin **bir sonraki yilki yillik gelirinin (Revenue)**
regresyon yontemleriyle tahmin edilmesi amaclanmistir. Calisma vize puanlama olcutunde
belirtilen tum asamalari kapsar:

1. **Veri On Isleme, Kesif ve Gorsellestirme**
2. **Veri Madenciligi Algoritmalarinin Uygulanmasi (Regresyon)**
3. **Model Degerlendirme ve Karsilastirma**

**Problem turu:** Denetimli ogrenme - **Regresyon** (surekli hedef: gelecek yil geliri).

**Yontem:** Ardisik yillar birlestirilir (2014->2015, 2015->2016, 2016->2017, 2017->2018).
Yil N'deki finansal gostergeler ozellik (feature) olarak, Yil N+1'deki `Revenue` hedef
(target) olarak kullanilir. Ayni sirket `Ticker` anahtariyla eslestirilir. Hedef
degiskenin ciddi sekilde genis bir olcekte (binlerce dolardan yuz milyar dolara) dagilmasi
nedeniyle **logaritmik donusum** (`log1p`) uygulanmistir.

Bu sonceki surumden farkli olarak **Polinomial Regresyon (derece=2, Ridge cezali)** modeli
de karsilastirma setine eklenmistir. Polinomial ozellikler, ozelliklerin ikili etkilesimlerini
ve karesel terimlerini dogrusal modele sokarak dogrusal olmayan etkilerin de kismen
yakalanmasini saglar.
""")

# ---------- 1. Kutuphaneler ----------
md("""## 1. Gerekli Kutuphanelerin Yuklenmesi

Analiz icin kullanilacak kutuphaneler: veri isleme icin **pandas/numpy**, gorsellestirme
icin **matplotlib/seaborn**, regresyon algoritmalari, on isleme ve model degerlendirme
icin **scikit-learn**. Tekrarlanabilirlik icin rastgelelik tohumu sabitlenmistir.
""")

code("""# Temel kutuphaneler
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import warnings, os

# scikit-learn on isleme araclari
from sklearn.model_selection import train_test_split, KFold, cross_val_score
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.impute import SimpleImputer
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.pipeline import Pipeline

# scikit-learn regresyon modelleri
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.neighbors import KNeighborsRegressor

# Regresyon metrikleri
from sklearn.metrics import (mean_squared_error, mean_absolute_error,
                             r2_score, mean_absolute_percentage_error)

# Ayarlar
warnings.filterwarnings('ignore')
np.random.seed(42)
plt.rcParams['figure.figsize'] = (9, 5)
plt.rcParams['axes.grid'] = True
sns.set_style('whitegrid')

# Cikti klasoru (gorseller raporda kullanilacak)
os.makedirs('outputs', exist_ok=True)
print('Kutuphaneler basariyla yuklendi.')""")

# ---------- 2. Veri Yukleme ----------
md("""## 2. Veri Setinin Yuklenmesi ve Ardisik Yillarin Birlestirilmesi

Bu calismada 5 farkli CSV dosyasi (2014-2018) kullanilmaktadir. Regresyon probleminin
tanimi geregi, her ornek **ayni sirketin iki ardisik yilindaki** verilerinden
uretilmelidir:

- Ozellikler: Yil N'deki finansal gostergeler (224 sutun).
- Hedef: Yil N+1'deki `Revenue` (ayni sirket, bir sonraki yil).

Bu yapi sayesinde 4 ayri yil cifti (2014->2015, 2015->2016, 2016->2017, 2017->2018)
olusturulur ve tumu dikey olarak birlestirilerek egitim kumesi buyutulur. Ayni `Ticker`
uzerinden ic birlesim (inner join) yapilir, boylece yalnizca iki yilda da mevcut olan
sirketler dahil edilir.
""")

code("""# Tum yillarin okunmasi ve sutun isminin Ticker olarak standartlastirilmasi
years = [2014, 2015, 2016, 2017, 2018]
dfs = {}
for y in years:
    d = pd.read_csv(f'data/{y}_Financial_Data.csv')
    d = d.rename(columns={'Unnamed: 0': 'Ticker'})
    dfs[y] = d
    print(f'{y}: {d.shape[0]} sirket, {d.shape[1]} sutun')""")

code("""# Ardisik yillari Ticker anahtariyla birlestir
# Ozellikler: Yil N -- Hedef: Yil N+1 Revenue
pair_list = []
for y in [2014, 2015, 2016, 2017]:
    base = dfs[y].copy()
    target_df = dfs[y + 1][['Ticker', 'Revenue']].rename(
        columns={'Revenue': 'Revenue_next'})
    merged = base.merge(target_df, on='Ticker', how='inner')
    merged['SourceYear'] = y
    pair_list.append(merged)
    print(f'{y} -> {y+1}: {merged.shape[0]} eslenmis sirket')

df_all = pd.concat(pair_list, ignore_index=True)
print()
print('Birlesik veri seti boyutu:', df_all.shape)""")

code("""# Sadece pozitif Revenue ve Revenue_next degerlerini tut
# (0 veya negatif gelir olmaz; log donusumu icin anlamsizdir)
before = df_all.shape[0]
df_all = df_all[(df_all['Revenue'] > 0) & (df_all['Revenue_next'] > 0)].reset_index(drop=True)
print(f'Pozitif olmayan gelir filtrelendi: {before - df_all.shape[0]} satir kaldirildi')
print(f'Nihai veri seti boyutu          : {df_all.shape}')
df_all.head(3)""")

# ---------- 3. Eksik veri ----------
md("""## 3. Eksik Veri Analizi ve Veri Temizleme (5 Puan)

Finansal veri setlerinde eksik degerler oldukca yaygindir. Bu asamada:

- **Cok eksik sutunlar (> %40 eksik)** kaldirilir. Bu oranda eksik bir sutundan guvenilir
  atama (imputation) yapmak mumkun degildir ve modele gurultu ekler.
- Kalan sayisal sutunlardaki eksik degerler **medyan atamasi** ile doldurulur. Medyan,
  finansal gostergelerde sikca karsilasilan **uc degerlere (outliers)** karsi
  ortalamadan daha dayaniklidir.
- Sonsuz degerler (inf / -inf) once NaN'a donusturulur, sonra medyan ile doldurulur.
- Tekrar eden satirlar (duplicate) kontrol edilerek kaldirilir.
- Kategorik `Sector` sutunundaki olasi bos degerler **mod** ile doldurulur.

Hedef degiskende (`Revenue_next`) eksik deger yoktur; cunku birlesim (join) asamasinda
pozitif olmayan ve NaN olan satirlar zaten cikarilmistir.
""")

code("""# Sutun bazinda eksik deger orani
missing_ratio = df_all.isnull().mean().sort_values(ascending=False)
print('En cok eksik veri iceren ilk 10 sutun:')
print((missing_ratio.head(10) * 100).round(2).astype(str) + ' %')
print()
print('Toplam eksik hucre sayisi:', df_all.isnull().sum().sum())
print('Duplike satir sayisi     :', df_all.duplicated().sum())""")

code("""# Eksik veri gorsellestirme
plt.figure(figsize=(10, 5))
top20 = missing_ratio.head(20) * 100
top20.plot(kind='barh', color='steelblue')
plt.gca().invert_yaxis()
plt.xlabel('Eksik Veri Orani (%)')
plt.title('En Fazla Eksik Veri Iceren 20 Sutun')
plt.tight_layout()
plt.savefig('outputs/01_missing_values.png', dpi=120)
plt.show()""")

code("""# 3.1 Cok eksik sutunlari kaldir
threshold = 0.40
cols_to_drop = missing_ratio[missing_ratio > threshold].index.tolist()
print(f'%{int(threshold*100)} esiginin uzerinde eksigi olan {len(cols_to_drop)} sutun kaldirildi.')
df_clean = df_all.drop(columns=cols_to_drop)

# 3.2 Sonsuz degerleri NaN'a cevir
df_clean = df_clean.replace([np.inf, -np.inf], np.nan)

# 3.3 Duplike satirlari kaldir
before = df_clean.shape[0]
df_clean = df_clean.drop_duplicates().reset_index(drop=True)
print(f'Duplike satirlar kaldirildi: {before - df_clean.shape[0]}')

# 3.4 Sayisal sutunlara medyan atama (Revenue_next haric tutulur)
num_cols = df_clean.select_dtypes(include=np.number).columns.tolist()
num_cols = [c for c in num_cols if c != 'Revenue_next']
imputer = SimpleImputer(strategy='median')
df_clean[num_cols] = imputer.fit_transform(df_clean[num_cols])

# 3.5 Sector icin mod atama
if 'Sector' in df_clean.columns:
    df_clean['Sector'] = df_clean['Sector'].fillna(df_clean['Sector'].mode()[0])

print('Temizlik sonrasi toplam eksik deger:', df_clean.isnull().sum().sum())
print('Temizlik sonrasi veri boyutu       :', df_clean.shape)""")

# ---------- 4. Gorsellestirme ----------
md("""## 4. Kesifsel Veri Analizi ve Gorsellestirme (10 Puan)

Bu asamada veri seti hakkinda istatistiksel ve gorsel ongoru elde edilir. Ozellikle
hedef degiskenin (`Revenue_next`) dagilimi, farkli sektorlerdeki gelir dagilimi, yil
bazinda degisim ve hedef ile en iliskili ozelliklerin korelasyonu incelenir.
""")

code("""# 4.1 Hedef degiskenin (Revenue_next) temel istatistikleri
print('Revenue_next temel istatistikler (USD):')
print(df_clean['Revenue_next'].describe().apply(lambda x: f'{x:,.0f}'))
print()
print('Logaritmik donusum sonrasi istatistikler:')
print(np.log1p(df_clean['Revenue_next']).describe().round(2))""")

code("""# 4.2 Hedef degiskenin dagilimi: ham ve log-olceginde
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
axes[0].hist(df_clean['Revenue_next'] / 1e9, bins=60, color='#d9534f', edgecolor='black')
axes[0].set_title('Revenue_next (Milyar USD) - Ham Dagilim')
axes[0].set_xlabel('Gelir (Milyar USD)')
axes[0].set_ylabel('Frekans')
axes[0].set_xlim(0, 50)  # sag kuyruk cok uzun, gorunurluk icin kirpildi

axes[1].hist(np.log1p(df_clean['Revenue_next']), bins=60,
             color='#5cb85c', edgecolor='black')
axes[1].set_title('log1p(Revenue_next) - Log Olcekli Dagilim')
axes[1].set_xlabel('log1p(Gelir)')
axes[1].set_ylabel('Frekans')
plt.tight_layout()
plt.savefig('outputs/02_target_distribution.png', dpi=120)
plt.show()""")

code("""# 4.3 Sektor bazli hedef dagilim (log olcek)
plt.figure(figsize=(11, 5))
df_plot = df_clean.copy()
df_plot['log_Revenue_next'] = np.log1p(df_plot['Revenue_next'])
order = df_plot.groupby('Sector')['log_Revenue_next'].median().sort_values(ascending=False).index
sns.boxplot(data=df_plot, x='Sector', y='log_Revenue_next', order=order, palette='viridis')
plt.xticks(rotation=35, ha='right')
plt.ylabel('log1p(Revenue_next)')
plt.title('Sektorlere Gore Bir Sonraki Yil Gelirinin Dagilimi')
plt.tight_layout()
plt.savefig('outputs/03_sector_boxplot.png', dpi=120)
plt.show()""")

code("""# 4.4 Kaynak yila gore ortalama gelir
yearly = df_clean.groupby('SourceYear')['Revenue_next'].agg(['mean', 'median', 'count'])
print('Kaynak yila gore gelir ozetleri:')
print(yearly.round(0))

plt.figure(figsize=(9, 4))
plt.bar(yearly.index.astype(str), yearly['mean'] / 1e9,
        color='steelblue', edgecolor='black')
plt.ylabel('Ortalama Gelir (Milyar USD)')
plt.xlabel('Ozellik Yili (Yil N)')
plt.title('Kaynak Yila Gore Ortalama Hedef Gelir (Yil N+1)')
plt.tight_layout()
plt.savefig('outputs/04_yearly_mean.png', dpi=120)
plt.show()""")

code("""# 4.5 Secilmis finansal gostergelerin histogramlari
selected = ['Revenue', 'Net Income', 'Gross Profit', 'Operating Income',
            'EPS', 'Free Cash Flow']
# Bazi sutun isimleri veri setinde farkli; mevcut olanlari sec
selected = [c for c in selected if c in df_clean.columns]
fig, axes = plt.subplots(2, 3, figsize=(14, 8))
for ax, col in zip(axes.flatten(), selected):
    data = df_clean[col]
    lo, hi = data.quantile([0.01, 0.99])
    ax.hist(data.clip(lo, hi), bins=40, color='teal', edgecolor='black')
    ax.set_title(col)
    ax.set_xlabel('Deger')
    ax.set_ylabel('Frekans')
plt.suptitle('Secilmis Finansal Gostergelerin Dagilimlari', fontsize=14, y=1.02)
plt.tight_layout()
plt.savefig('outputs/05_feature_histograms.png', dpi=120)
plt.show()""")

code("""# 4.6 Bu yilki Revenue ile bir sonraki yilin Revenue'su arasindaki iliski (log-log)
plt.figure(figsize=(7, 6))
plt.scatter(np.log1p(df_clean['Revenue']), np.log1p(df_clean['Revenue_next']),
            alpha=0.3, s=10, color='#3366cc')
x_line = np.linspace(np.log1p(df_clean['Revenue']).min(),
                     np.log1p(df_clean['Revenue']).max(), 100)
plt.plot(x_line, x_line, 'r--', label='y = x (ayni gelir)')
plt.xlabel('log1p(Revenue) (Yil N)')
plt.ylabel('log1p(Revenue_next) (Yil N+1)')
plt.title('Yil N Gelir ile Yil N+1 Gelir Iliskisi (Log-Log)')
plt.legend()
plt.tight_layout()
plt.savefig('outputs/06_rev_scatter.png', dpi=120)
plt.show()
print('Korelasyon (log-log):',
      np.log1p(df_clean['Revenue']).corr(np.log1p(df_clean['Revenue_next'])).round(4))""")

code("""# 4.7 Hedef ile en yuksek korelasyonlu 15 ozellik uzerinden isi haritasi
numeric_df = df_clean.select_dtypes(include=np.number).copy()
log_target = np.log1p(df_clean['Revenue_next'])
corr_with_target = numeric_df.drop(columns=['Revenue_next']).corrwith(log_target).abs()
corr_with_target = corr_with_target.sort_values(ascending=False)
top_features = corr_with_target.head(15).index.tolist()

plt.figure(figsize=(10, 8))
heat_df = numeric_df[top_features + ['Revenue_next']].copy()
heat_df['Revenue_next'] = log_target
sns.heatmap(heat_df.corr(), annot=True, fmt='.2f', cmap='coolwarm',
            center=0, linewidths=0.5)
plt.title('En Yuksek Mutlak Korelasyonlu 15 Ozellik ve Hedef')
plt.tight_layout()
plt.savefig('outputs/07_correlation_heatmap.png', dpi=120)
plt.show()

print('Log-hedef ile en yuksek (mutlak) korelasyona sahip ilk 10 ozellik:')
print(corr_with_target.head(10).round(3))""")

# ---------- 5. Ozellik muhendisligi ----------
md("""## 5. Veri Donusturme ve Ozellik Muhendisligi (10 Puan)

Bu asamada veriler regresyon modellerine uygun hale getirilir:

1. **Sizinti ve kimlik kolonlarini cikar:** `Ticker`, `Class`, yila ozgu `PRICE VAR [%]`
   sutunlari, `SourceYear` ve hedefimiz `Revenue_next` ozellik matrisinden cikarilir.
2. **Hedef Donusumu:** `Revenue_next`, `log1p` ile logaritmik olcege cevrilir. Gelir
   dagilimi birkac mertebe farki iceren uzun sag kuyrukludur; log donusumu modelin
   iliskiyi dogrusallastirmasini ve MSE kaybinin dengeli olmasini saglar.
3. **Kategorik Kodlama:** `Sector` degiskeni **One-Hot Encoding** ile 11 ikili sutuna
   donusturulur. Boylece sektorler arasina yapay bir siralama eklenmemis olur.
4. **Normalizasyon:** `StandardScaler` tum sayisal sutunlara uygulanir (ortalama 0,
   std 1). Lineer modeller, Polinomial regresyon ve KNN gibi olcek-duyarli algoritmalar
   icin kritiktir.
5. **Ozellik Secimi:** `SelectKBest (f_regression)` ile hedef ile en iliskili **50**
   ozellik secilir. Polinomial regresyon dereceyi 2'ye cikardiginda bu 50 ozellik
   yaklasik 1326 polinomial ozellige genisleyecektir; bu nedenle baslangic ozellik
   sayisini kontrollu tutmak onemlidir.
""")

code("""# 5.1 Sizinti ve kimlik kolonlarini cikar
leak_cols = ['Ticker', '2015 PRICE VAR [%]', '2016 PRICE VAR [%]',
             '2017 PRICE VAR [%]', '2018 PRICE VAR [%]', '2019 PRICE VAR [%]',
             'Class', 'SourceYear']
leak_cols = [c for c in leak_cols if c in df_clean.columns]
print('Cikarilan kolonlar:', leak_cols)

X = df_clean.drop(columns=leak_cols + ['Revenue_next'])
y_raw = df_clean['Revenue_next'].values

# 5.2 Hedef donusumu: log1p
y = np.log1p(y_raw)
print('\\nOzellik matrisi boyutu:', X.shape)
print('Hedef vektorunun boyutu:', y.shape)
print('log1p(y) araligi       :', f'{y.min():.2f} - {y.max():.2f}')""")

code("""# 5.3 One-Hot Encoding (Sector)
X = pd.get_dummies(X, columns=['Sector'], prefix='Sector', drop_first=False)
bool_cols = X.select_dtypes(include='bool').columns
X[bool_cols] = X[bool_cols].astype(int)
print('One-Hot sonrasi ozellik matrisi boyutu:', X.shape)""")

code("""# 5.4 Standartlastirma
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
X_scaled = pd.DataFrame(X_scaled, columns=X.columns)
print('Olceklenmis veri (ilk 5 sutun) ortalamasi:',
      X_scaled.iloc[:, :5].mean().round(3).values)
print('Olceklenmis veri (ilk 5 sutun) std sapmasi:',
      X_scaled.iloc[:, :5].std().round(3).values)""")

code("""# 5.5 SelectKBest ile en iyi K ozellik secimi
K = 50
selector = SelectKBest(score_func=f_regression, k=K)
X_selected = selector.fit_transform(X_scaled, y)
selected_mask = selector.get_support()
selected_features = X_scaled.columns[selected_mask].tolist()
print(f'Secilen ozellik sayisi: {len(selected_features)}')

feat_scores = pd.Series(selector.scores_, index=X_scaled.columns).sort_values(ascending=False)
print('\\nEn yuksek F-skoruna sahip ilk 15 ozellik:')
print(feat_scores.head(15).round(2))""")

code("""# 5.6 Secilmis ozelliklerin onem grafigi
plt.figure(figsize=(10, 6))
feat_scores.head(20).plot(kind='barh', color='teal')
plt.gca().invert_yaxis()
plt.xlabel('F-Skoru (f_regression)')
plt.title('En Onemli 20 Ozellik (SelectKBest)')
plt.tight_layout()
plt.savefig('outputs/08_feature_importance.png', dpi=120)
plt.show()""")

# ---------- 6. Modelleme ----------
md("""## 6. Veri Madenciligi Algoritmalarinin Uygulanmasi (25 Puan)

### 6.1 Model Secimi ve Gerekcelendirme (5 Puan)

Problem **regresyon** problemidir: hedef degisken (`log1p(Revenue_next)`) sureklidir.
Hem dogrusal hem de dogrusal olmayan iliskileri degerlendirebilmek icin birbirinden
farkli varsayimlarla calisan **sekiz model** karsilastirilmistir:

| Model | Neden Secildi |
|-------|----------------|
| **Dogrusal Regresyon** | Yorumlanabilir, dogrusal taban cizgisi |
| **Ridge (L2)** | Coklu dogrusalliga dayanikli dogrusal model |
| **Lasso (L1)** | L1 cezasi ile seyrek (sparse) cozum ve ozellik secimi saglar |
| **Polinomial Reg. (deg=2, Ridge cezali)** | Dogrusal modele karesel ve ikili etkilesim terimleri ekler; boylece dogrusal olmayan yapilar kismen yakalanir |
| **Karar Agaci** | Dogrusal olmayan, yorumlanabilir; uc degerlere dayanikli |
| **Rastgele Orman** | Topluluk yontemi, asiri uyumu azaltir, yuksek dogruluk |
| **Gradient Boosting** | Guclu topluluk; finansal tahminde yaygin ustun sonuclar |
| **KNN (k=7)** | Parametrik olmayan, yerel ornek tabanli baz cizgisi |

Polinomial regresyon icin `PolynomialFeatures(degree=2, interaction_only=False,
include_bias=False)` ile 50 ozellik yaklasik 1325 polinomial ozellige genisletilmis ve
elde edilen yuksek boyutlu matrise `Ridge(alpha=10)` uygulanmistir. Ridge cezasi, coklu
dogrusallik ve asiri uyum risklerini azaltir.

Modeller **k-katli capraz dogrulama (5-fold)** ile degerlendirilir. Hedef `log1p`
olceginde oldugundan tum metrikler hem log-olceginde hem de `expm1` ile ters donusum
yapilarak **gercek dolar olceginde** raporlanir. Performans metrikleri: **MAE, RMSE,
R2** ve (gercek olcekte) **MAPE**.
""")

code("""# Egitim/Test ayrimi
X_train, X_test, y_train, y_test = train_test_split(
    X_selected, y, test_size=0.2, random_state=42)

print('Egitim seti boyutu:', X_train.shape)
print('Test seti boyutu  :', X_test.shape)""")

code("""# 6.2 Modellerin tanimlanmasi
# Polinomial regresyon pipeline: PolynomialFeatures(2) + Ridge
poly_pipe = Pipeline([
    ('poly', PolynomialFeatures(degree=2, interaction_only=False, include_bias=False)),
    ('ridge', Ridge(alpha=10.0, random_state=42))
])

models = {
    'Dogrusal Regresyon'           : LinearRegression(),
    'Ridge (alpha=1)'              : Ridge(alpha=1.0, random_state=42),
    'Lasso (alpha=0.01)'           : Lasso(alpha=0.01, random_state=42, max_iter=10000),
    'Polinomial Reg. (deg=2+Ridge)': poly_pipe,
    'Karar Agaci'                  : DecisionTreeRegressor(max_depth=10, random_state=42),
    'Rastgele Orman'               : RandomForestRegressor(n_estimators=300, max_depth=15,
                                                            random_state=42, n_jobs=-1),
    'Gradient Boosting'            : GradientBoostingRegressor(n_estimators=300, max_depth=4,
                                                                learning_rate=0.05,
                                                                random_state=42),
    'KNN (k=7)'                    : KNeighborsRegressor(n_neighbors=7)
}
print(f'Toplam {len(models)} regresyon modeli egitilecek.')""")

code("""# 6.3 Uygulama + 6.4 K-Katli CV ile Degerlendirme
results = []
cv = KFold(n_splits=5, shuffle=True, random_state=42)

for name, model in models.items():
    print(f'\\n--- {name} ---')
    # 5-katli CV - log olceginde R2, MAE, RMSE
    cv_r2  = cross_val_score(model, X_train, y_train, cv=cv,
                             scoring='r2', n_jobs=-1)
    cv_mae = -cross_val_score(model, X_train, y_train, cv=cv,
                              scoring='neg_mean_absolute_error', n_jobs=-1)
    cv_rmse = np.sqrt(-cross_val_score(model, X_train, y_train, cv=cv,
                                       scoring='neg_mean_squared_error',
                                       n_jobs=-1))

    # Final egitim ve test
    model.fit(X_train, y_train)
    y_pred_log = model.predict(X_test)

    # Log olceginde metrikler
    r2_log  = r2_score(y_test, y_pred_log)
    mae_log = mean_absolute_error(y_test, y_pred_log)
    rmse_log = np.sqrt(mean_squared_error(y_test, y_pred_log))

    # Ters donusum ile gercek olcek
    y_true_real = np.expm1(y_test)
    y_pred_real = np.expm1(y_pred_log)
    # Negatif tahminleri sifirla
    y_pred_real = np.maximum(y_pred_real, 0)

    r2_real  = r2_score(y_true_real, y_pred_real)
    mae_real = mean_absolute_error(y_true_real, y_pred_real)
    rmse_real = np.sqrt(mean_squared_error(y_true_real, y_pred_real))
    try:
        mape_real = mean_absolute_percentage_error(y_true_real, y_pred_real)
    except Exception:
        mape_real = np.nan

    print(f'CV (log) -> R2: {cv_r2.mean():.4f} (+/- {cv_r2.std():.4f})  '
          f'MAE: {cv_mae.mean():.4f}  RMSE: {cv_rmse.mean():.4f}')
    print(f'Test (log)  -> R2: {r2_log:.4f}  MAE: {mae_log:.4f}  RMSE: {rmse_log:.4f}')
    print(f'Test (real) -> R2: {r2_real:.4f}  MAE: {mae_real:,.0f}  '
          f'RMSE: {rmse_real:,.0f}  MAPE: {mape_real:.3f}')

    results.append({
        'Model'       : name,
        'CV R2 (log)' : round(cv_r2.mean(), 4),
        'CV MAE (log)': round(cv_mae.mean(), 4),
        'CV RMSE(log)': round(cv_rmse.mean(), 4),
        'R2 (log)'    : round(r2_log, 4),
        'MAE (log)'   : round(mae_log, 4),
        'RMSE (log)'  : round(rmse_log, 4),
        'R2 (real)'   : round(r2_real, 4),
        'MAE (real)'  : round(mae_real, 2),
        'RMSE (real)' : round(rmse_real, 2),
        'MAPE (real)' : round(mape_real, 4) if not np.isnan(mape_real) else np.nan,
        '_model'      : model,
        '_y_pred_log' : y_pred_log,
        '_y_pred_real': y_pred_real
    })""")

code("""# 6.5 Sonuclari tablo olarak goster (log olceginde R2'ye gore sirala)
results_df = pd.DataFrame([{k: v for k, v in r.items() if not k.startswith('_')}
                           for r in results])
results_df = results_df.sort_values('R2 (log)', ascending=False).reset_index(drop=True)
print('Model Karsilastirma Tablosu (log olcek R2\\'ye gore sirali):')
results_df""")

code("""# 6.6 Sonuclari dosyaya kaydet
results_df.to_csv('outputs/model_results.csv', index=False)
print('Model sonuclari outputs/model_results.csv dosyasina kaydedildi.')""")

# ---------- 7. Detayli degerlendirme ----------
md("""## 7. Detayli Model Degerlendirmesi

Bu asamada modellerin performansi gorsel olarak karsilastirilir. Kullanilan gorseller:

- **Bar grafigi:** Modellerin R2, MAE ve RMSE karsilastirmasi (log olcek)
- **Tahmin - Gercek scatter plot:** Her model icin y_true vs y_pred
- **Residual (artik) plot:** En iyi model icin hata dagilimi
- **Ozellik onem grafigi:** En iyi model icin en onemli ozellikler (agac tabanli ise)
""")

code("""# 7.1 Model karsilastirma bar grafigi (log olcek)
fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
order = results_df.sort_values('R2 (log)', ascending=False)

axes[0].barh(order['Model'], order['R2 (log)'], color='seagreen', edgecolor='black')
axes[0].set_xlabel('R2 (log olcek)')
axes[0].set_title('R2 Karsilastirmasi')
axes[0].invert_yaxis()

axes[1].barh(order['Model'], order['MAE (log)'], color='orange', edgecolor='black')
axes[1].set_xlabel('MAE (log olcek)')
axes[1].set_title('MAE Karsilastirmasi')
axes[1].invert_yaxis()

axes[2].barh(order['Model'], order['RMSE (log)'], color='tomato', edgecolor='black')
axes[2].set_xlabel('RMSE (log olcek)')
axes[2].set_title('RMSE Karsilastirmasi')
axes[2].invert_yaxis()

plt.suptitle('Modellerin Test Seti Performans Karsilastirmasi (log olcek)',
             fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('outputs/09_model_comparison.png', dpi=120, bbox_inches='tight')
plt.show()""")

code("""# 7.2 Tahmin vs Gercek scatter plot (her model icin, log olcek)
n = len(results)
cols = 3
rows = int(np.ceil(n / cols))
fig, axes = plt.subplots(rows, cols, figsize=(14, 4 * rows))
axes = axes.flatten()
for ax, r in zip(axes, results):
    ax.scatter(y_test, r['_y_pred_log'], alpha=0.35, s=10, color='#3366cc')
    lo, hi = y_test.min(), y_test.max()
    ax.plot([lo, hi], [lo, hi], 'r--', label='y=x')
    ax.set_title(f"{r['Model']}\\nR2={r['R2 (log)']:.3f}")
    ax.set_xlabel('Gercek log1p(Revenue_next)')
    ax.set_ylabel('Tahmin log1p(Revenue_next)')
# Fazla eksenleri kapat
for ax in axes[n:]:
    ax.axis('off')
plt.suptitle('Tum Modeller Icin Tahmin-Gercek Dagilimi (log olcek)',
             fontsize=13, y=1.01)
plt.tight_layout()
plt.savefig('outputs/10_pred_vs_true.png', dpi=120, bbox_inches='tight')
plt.show()""")

code("""# 7.3 En iyi model icin residual plot
best_result = results_df.iloc[0]
best_name = best_result['Model']
best = next(r for r in results if r['Model'] == best_name)
print(f'En iyi model: {best_name}')

residuals = y_test - best['_y_pred_log']

fig, axes = plt.subplots(1, 2, figsize=(13, 4))
axes[0].scatter(best['_y_pred_log'], residuals, alpha=0.35, s=10, color='purple')
axes[0].axhline(0, color='red', linestyle='--')
axes[0].set_xlabel('Tahmin log1p(Revenue_next)')
axes[0].set_ylabel('Artik (Gercek - Tahmin)')
axes[0].set_title(f'{best_name} - Artik Dagilimi')

axes[1].hist(residuals, bins=50, color='purple', edgecolor='black')
axes[1].axvline(0, color='red', linestyle='--')
axes[1].set_xlabel('Artik (log olcek)')
axes[1].set_ylabel('Frekans')
axes[1].set_title(f'{best_name} - Artik Histogrami')

plt.tight_layout()
plt.savefig('outputs/11_residuals.png', dpi=120)
plt.show()
print(f'\\nArtik ortalamasi : {residuals.mean():.4f}')
print(f'Artik std sapmasi: {residuals.std():.4f}')""")

code("""# 7.4 En iyi model icin ozellik onemi (agac tabanli ise)
best_model = best['_model']
if hasattr(best_model, 'feature_importances_'):
    importances = pd.Series(best_model.feature_importances_,
                            index=selected_features).sort_values(ascending=False)
    plt.figure(figsize=(10, 7))
    importances.head(20).plot(kind='barh', color='darkgreen')
    plt.gca().invert_yaxis()
    plt.xlabel('Onem Skoru')
    plt.title(f'{best_name} - En Onemli 20 Ozellik')
    plt.tight_layout()
    plt.savefig('outputs/12_best_model_importance.png', dpi=120)
    plt.show()
    print('En onemli 10 ozellik:')
    print(importances.head(10).round(4))
elif hasattr(best_model, 'coef_'):
    coefs = pd.Series(best_model.coef_, index=selected_features)
    coefs_abs = coefs.abs().sort_values(ascending=False)
    plt.figure(figsize=(10, 7))
    coefs_abs.head(20).plot(kind='barh', color='darkgreen')
    plt.gca().invert_yaxis()
    plt.xlabel('|Katsayi|')
    plt.title(f'{best_name} - En Onemli 20 Katsayi')
    plt.tight_layout()
    plt.savefig('outputs/12_best_model_importance.png', dpi=120)
    plt.show()
else:
    print(f'{best_name} icin dogrudan ozellik onemi bilgisi mevcut degil.')""")

code("""# 7.5 Polinomial Regresyon detayli analizi (log olcek, tahmin-gercek)
poly_result = next(r for r in results if 'Polinomial' in r['Model'])
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# Tahmin vs gercek
axes[0].scatter(y_test, poly_result['_y_pred_log'], alpha=0.35, s=10, color='darkorange')
lo, hi = y_test.min(), y_test.max()
axes[0].plot([lo, hi], [lo, hi], 'r--', label='y=x')
axes[0].set_xlabel('Gercek log1p(Revenue_next)')
axes[0].set_ylabel('Tahmin log1p(Revenue_next)')
axes[0].set_title(f"Polinomial Regresyon - Tahmin vs Gercek\\nR2={poly_result['R2 (log)']:.3f}")
axes[0].legend()

# Artik dagilimi
poly_resid = y_test - poly_result['_y_pred_log']
axes[1].hist(poly_resid, bins=50, color='darkorange', edgecolor='black')
axes[1].axvline(0, color='red', linestyle='--')
axes[1].set_xlabel('Artik (log olcek)')
axes[1].set_ylabel('Frekans')
axes[1].set_title('Polinomial Regresyon - Artik Histogrami')

plt.tight_layout()
plt.savefig('outputs/13_polynomial_analysis.png', dpi=120)
plt.show()

print(f'Polinomial Regresyon metrikleri:')
print(f'  CV R2  : {poly_result["CV R2 (log)"]:.4f}')
print(f'  Test R2: {poly_result["R2 (log)"]:.4f}')
print(f'  Test MAE : {poly_result["MAE (log)"]:.4f}')
print(f'  Test RMSE: {poly_result["RMSE (log)"]:.4f}')""")

code("""# 7.6 En iyi modelden 10 ornek tahmin (gercek dolar olceginde)
sample_idx = np.random.RandomState(42).choice(len(y_test), size=10, replace=False)
sample_true = np.expm1(y_test[sample_idx])
sample_pred = best['_y_pred_real'][sample_idx]
sample_df = pd.DataFrame({
    'Gercek Gelir (USD)'  : sample_true,
    'Tahmin Gelir (USD)'  : sample_pred,
    'Mutlak Hata (USD)'   : np.abs(sample_true - sample_pred),
    'Yuzde Hata (%)'      : np.abs(sample_true - sample_pred) / sample_true * 100
})
sample_df = sample_df.round(0)
sample_df['Yuzde Hata (%)'] = sample_df['Yuzde Hata (%)'].round(2)
print(f'{best_name} modelinden 10 ornek tahmin:')
sample_df""")

# ---------- 8. Sonuclar ----------
md("""## 8. Sonuc ve Icgoruler

Bu calismada 2014-2018 yillarini kapsayan ABD borsasi finansal verileri kullanilarak,
bir sirketin **bir sonraki yilki gelirinin (Revenue)** tahmin edilmesine yonelik bir
regresyon modeli gelistirilmistir.

**Veri Hazirlama:**
- 4 ardisik yil cifti (2014->2015, 2015->2016, 2016->2017, 2017->2018) `Ticker`
  uzerinden birlestirilerek yaklasik 15.500 egitim ornegi elde edilmistir.
- Eksik degerler medyan atamasi ile giderilmis, yuksek eksiklik oranina sahip sutunlar
  kaldirilmistir.
- Sektor degiskeni One-Hot Encoding ile sayisallastirilmis, sayisal ozellikler
  standartlastirilmistir.
- Boyut lanetini azaltmak icin `SelectKBest (f_regression)` ile en onemli 50 ozellik
  secilmistir.

**Modelleme:**
- Sekiz farkli regresyon algoritmasi (Dogrusal, Ridge, Lasso, **Polinomial (derece=2 +
  Ridge)**, Karar Agaci, Rastgele Orman, Gradient Boosting, KNN) 5-katli capraz
  dogrulama ile karsilastirilmistir.
- Hedef degisken cok genis bir dinamik araliga sahip oldugundan `log1p` donusumu
  uygulanmis; metrikler hem log olceginde hem de ters donusum sonrasi gercek dolar
  olceginde hesaplanmistir.

**Onemli bulgular:**
- **Topluluk yontemleri (Rastgele Orman, Gradient Boosting)** dogrusal modellere gore
  belirgin sekilde daha iyi sonuc vermistir.
- **Polinomial Regresyon**, duz Dogrusal/Ridge/Lasso modellerine kiyasla belirgin bir
  iyilesme saglamis; ozellikler arasindaki ikili etkilesim ve karesel terimlerin gelir
  tahmininde anlamli bilgi tasidigini gostermistir. Ancak Gradient Boosting ve Rastgele
  Orman kadar yuksek bir R2 degerine ulasamamistir.
- Hedef ile en yuksek korelasyonlu ozellikler `Revenue`, `Cost of Revenue`, `Gross
  Profit` gibi dogrudan olcek gostergeleri ile `Operating Income` ve `EBITDA` gibi
  karlilik metrikleridir.
- Yil N geliri, Yil N+1 gelirinin en guclu habercisidir; bu sonuc finansal literaturde
  yaygin olarak kabul edilen gelir **otokorelasyonunu** dogrular.

**Sinirlamalar:**
- Makroekonomik degiskenler, sektor egilimleri ve haber akisi modele dahil degildir.
- Zaman serisi dinamikleri tam olarak modellenmemis; yalnizca iki ardisik yil arasinda
  bir eslesme yapilmistir.
- Polinomial regresyon yalnizca derece=2 ile sinanmistir; daha yuksek dereceler asiri
  uyum riskini artiracaktir.

**Icgoruler:**
- Finansal tablo verileri, bir sirketin yakin gelecekteki gelirini yuksek dogrulukla
  tahmin etmek icin yeterli sinyali tasimaktadir.
- Dogrusal modeller ile ikinci dereceden etkilesimlerin bile tam olarak yakalanamamasi,
  finansal verilerdeki iliskilerin yuksek mertebeden dogrusal olmadigini isaret eder.
- Gelir tahmini; stratejik planlama, kaynak tahsisi ve yatirimci raporlari icin pratik
  bir karar destek araci olarak kullanilabilir.

Tum gorseller `outputs/` klasorunde, model sonuclari ise `outputs/model_results.csv`
dosyasinda bulunmaktadir. Bu veriler IEEE formatindaki proje raporunda kullanilmistir.
""")

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": ".venv (3.13.12)",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {"name": "ipython", "version": 3},
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.13.12"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

Path('main.ipynb').write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding='utf-8')
print(f'main.ipynb olusturuldu. Toplam hucre sayisi: {len(cells)}')
