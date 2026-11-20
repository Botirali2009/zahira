# Qo'llanma manba fayllari

Bu papkadagi har bir `.txt` fayl — bitta rasmiy qo'llanma. Ilova birinchi
marta ishga tushganda (yoki `python scripts/ingest_guidelines.py` qo'lda
chaqirilganda) bu fayllar avtomatik `guideline_chunks` jadvaliga
(FTS5 qidiruv indeksi) bo'laklarga bo'linib yoziladi — triaj tahlilchisi
(`analyzers/llm_analyzer.py` yoki `analyzers/gemini_analyzer.py`, qaysi biri
faol bo'lsa) har javobni baholashdan oldin shu yerdan tegishli parchalarni
qidirib topadi.

## Format

Oddiy matn, bo'limlar `## Sarlavha` bilan ajratiladi:

```
## Diabetik ketoatsidoz (DKA) belgilari

Ta'rif: glyukoza > 11.0 mmol/l + keton belgilari + metabolik atsidoz.
Sekin rivojlanadi (3-4 kun).

Belgilari: nafasda aseton hidi, chuqur nafas olish, takroriy qusish...

## Gipoglikemiya belgilari

Ta'rif: glyukoza < 3.9 mmol/l. Tez rivojlanadi (daqiqalar).
...
```

- Har `## ` bilan boshlangan qator — yangi bo'lak (chunk) boshlanishi.
- Juda uzun bo'lim (~1200 belgidan katta) avtomatik ravishda paragraflar
  chegarasida qo'shimcha bo'laklarga bo'linadi — qo'lda tashvishlanish
  shart emas.
- Fayl nomi ahamiyatsiz, lekin manba nomi (`source_name`, qidiruv
  natijalarida ko'rinadigan) fayl ichidagi birinchi satr emas — u
  `scripts/ingest_guidelines.py` chaqirilganda parametr sifatida beriladi
  (pastga qarang) yoki fayl nomidan avtomatik olinadi.

## Qo'lda qayta yuklash

```bash
python scripts/ingest_guidelines.py data/guidelines/qollanma_1.txt "Milliy klinik protokol 180-son"
```

Manba nomini bermasangiz, fayl nomidan olinadi (`qollanma_1.txt` -> `qollanma_1`).
Bir xil manba nomi bilan qayta ishga tushirish avvalgi bo'laklarni almashtiradi
(eskilari o'chadi, dublikat bo'lmaydi).
