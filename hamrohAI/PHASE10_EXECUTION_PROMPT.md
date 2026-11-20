# Hamroh — Faza 10+ Ijro Prompti (Claude Code uchun)

> Bu faylni Claude Code'ga to'g'ridan-to'g'ri prompt sifatida bering. Bu yerda faqat **g'oya va talablar**
> tasvirlangan — SQL, Python yoki boshqa kod yo'q. Sxema, fayl tuzilishi va implementatsiya
> tafsilotlarini o'zing, `CLAUDE.md` va `PLAN.md`dagi mavjud qoidalarga qat'iy amal qilgan holda,
> o'zing loyihalaysan.

---

## 0. Kontekst

Sen `hamroh` loyihasi ustida ishlayapsan. `CLAUDE.md` (qattiq qoidalar) va `PLAN.md` (arxitektura,
5 ta kengaytirish tamoyili) allaqachon mavjud va **majburiy** — bu hujjat ularni bekor qilmaydi,
ularning ustiga quradi. Xususan qat'iy amal qil:

- SQL faqat `repos/`da. Routes — HTTP, services — logika.
- Yangi xatti-harakat = **yangi fayl** `analyzers/`, `hooks/` yoki `notifiers/` ichida — mavjud faylga
  `if` qo'shish emas.
- Sxema o'zgarishi = yangi raqamlangan `migrations/*.sql` fayli. Qo'llanilgan migratsiyaga tegma.
- Tugallanmagan funksiya `config.FEATURES` orqali o'chirilgan holda merge bo'ladi.
- Foydalanuvchiga ko'rinadigan matn — o'zbek tilida, lotin yozuvida. Kod/kommentariya/commit — ingliz tilida.
- Har vazifani tugatishdan oldin: ilovani ishga tushir, o'zgargan yo'lni sina, `pytest` ishlat, natijani ilova qil.

Quyida tasvirlangan funksionallik **7 ta modulga** bo'lingan (A–G). Har biri alohida faza/commit
bo'lishi kerak, tartibiga rioya qilib (3-bo'limga qara). Har modulni tugatgach to'xta, natijani
ko'rsat va keyingisiga o'tishdan oldin tasdiq kut — bularning barchasi bir committa qilinmasin.

---

## 1. Umumiy maqsad

Hozirgi Hamroh — check-in botiga va shifokor paneliga ega demo. Endi uni **haqiqiy ikki tomonlama
davolash platformasi**ga aylantiramiz: shifokorlar bemor qo'shadi yoki bemorlar o'zi ro'yxatdan
o'tadi, ikkala tomon ham dori tartibi va tashxisni boshqaradi, tizim tendensiyaga qarab motivatsiya
beradi, va bemorlar istalgan mavjud shifokordan **bir martalik** maslahat so'rashi mumkin.

Kirish tizimi hozircha Google va Telegram orqali bo'ladi, lekin **kelajakda dmed platformasi bilan
integratsiya qilinadi** — shuning uchun autentifikatsiya qatlami provayderga bog'lanmagan holda
loyihalanishi shart (1-modulga qara). dmed integratsiyasining o'zi **hozir amalga oshirilmaydi** —
faqat joyi tayyorlab qo'yiladi.

### Qabul qilingan taxminlar (kelishmasang, ayt — men shu asosda tuzdim)

- Konsultatsiya (Modul G) matn asosida bo'ladi, video/ovozli qo'ng'iroq shart emas (mavjud SmartCall
  faqat eslatma qo'ng'irog'i uchun, konsultatsiya uchun emas).
- Diplom/hujjat tekshiruvi (Modul B) hozircha qo'lda — avtomatik tasdiqlash keyingi bosqich.
- Taklif kodi (Modul C) **bitta bemorga oldindan bog'langan va bir martalik** — umumiy "klinikaga
  qo'shil" kodi emas, chunki shifokor ismni/tashxisni oldindan kiritadi.
- Doktorning "umumiy ulanish kodi" (Modul D — bemor o'zi ro'yxatdan o'tib, keyin ulanganda) esa
  **ko'p martalik va muddatli** — chunki u faqat bog'lash uchun, prefill uchun emas.
- Rasm/PDF fayllar hozircha faqat saqlanadi, ko'riladi; AI orqali avtomatik tahlil — alohida,
  kelajakdagi bosqich (hozir faqat kengaytma nuqtasi tayyorlab qo'yiladi).

---

## 2. Ijro tartibi va bog'liqlik

```
A (Auth)
 └─▶ B (Doktor profili)
      └─▶ C (Mijoz qo'shish + taklif kodi) ─┐
 └─▶ D (Bemor o'zi ro'yxatdan o'tishi) ──────┤
                                              ▼
                                   E (Dori + tashxis — umumiy jadval,
                                       B/C/D barchasi shunga tayanadi)
                                              │
                                              ▼
                                   F (Trend grafik + motivatsiya)

G (Konsultatsiya) — mustaqil, E tayyor bo'lgach istalgan payt qo'shiladi
```

A shart — hech narsa undan oldin ishlamaydi. B/C va D parallel yozilishi mumkin, lekin ikkalasi
ham E'ga muhtoj, shuning uchun E'dan oldin tugallanishi kerak. G eng oxiriga qoldirilsa xavfsiz.

---

## 3. Modul A — Autentifikatsiya: dmed'ga moslashuvchan arxitektura

### Muammo
Hozir tizimda umuman login yo'q (`patient_id`/`doctor_id` ochiq). Kelajakda uchinchi kirish usuli
(dmed) qo'shilishi rejalashtirilgan, lekin **hozir integratsiya qilinmaydi**. Shuning uchun
arxitektura shundayki, dmed keyin qo'shilganda faqat **bitta yangi fayl** yoziladi — mavjud login
oqimi, sessiya boshqaruvi yoki foydalanuvchi jadvaliga tegilmaydi.

### Talab
- Umumiy "identity provider" tushunchasi bo'lsin: har bir kirish usuli (Google, Telegram, dmed)
  bir xil shartnoma (interfeys)ni bajaradi — tashqi profildan kelib: provayder nomi, tashqi ID,
  to'liq ism, telefon (bo'lsa), email (bo'lsa).
- Google va Telegram uchun bu shartnoma **haqiqiy ishlaydigan** holatda amalga oshiriladi (OAuth /
  Telegram Login Widget).
- dmed uchun **xuddi shu shartnomani bajaradigan, lekin ichi bo'sh** joy tayyorlanadi — feature flag
  bilan o'chirilgan holatda. Hech qanday haqiqiy dmed API chaqiruvi yo'q.
- Bir foydalanuvchi bir nechta kirish usuliga ega bo'lishi **shart emas** hozircha — har provayder+
  tashqi ID juftligi alohida hisoblanadi (bitta odam ikki xil usul bilan kirsa, ikkita alohida
  hisob bo'ladi — kelajakda "hisoblarni birlashtirish" alohida masala, hozir yo'q).
- Har foydalanuvchining roli bor: bemor yoki shifokor. Ro'yxatdan o'tishning birinchi qadamida
  tanlanadi (yoki taklif kodi orqali kirilsa, avtomatik "bemor" bo'ladi).
- Sessiya himoyasi: shifokor faqat o'ziga bog'langan bemorlarni ko'rsin, bemor faqat o'z
  ma'lumotini ko'rsin. Buni har route darajasida tekshir, faqat UI darajasida yashirish yetarli emas.

### Tayyor bo'lish mezoni
Google va Telegram orqali haqiqiy login/logout ishlaydi, rol tanlanadi, keyingi modullar shu
sessiyaga tayanadi. dmed "provayder" ro'yxatda ko'rinadi lekin o'chirilgan (bosilsa — "hozircha
mavjud emas" degan tushunarli xabar, xato emas).

---

## 4. Modul B — Doktor ro'yxatdan o'tishi va profili

### Muammo
Shifokor tizimga kirganda uning kimligini, malakasini bilish kerak — bemorlar unga ishonishi va
tizim uni tegishli mutaxassislik bo'yicha (Modul G uchun) topa olishi uchun.

### Talab
Google/Telegram orqali birinchi marta "shifokor" sifatida kirgan foydalanuvchi profil to'ldirish
qadamidan o'tadi, ish qidirish platformalaridagiga o'xshash (LinkedIn/HH.uz uslubi):

- Shaxsiy: to'liq ism, tug'ilgan sana/yosh, telefon.
- Kasbiy: mutaxassislik/soha (bitta emas, bir nechta bo'lishi mumkin — Modul G buni ishlatadi),
  tajriba yillari, ish joyi (ixtiyoriy).
- Hujjatlar: diplom(lar), litsenziya — rasm yoki PDF sifatida yuklanadi, bir nechtasi bo'lishi mumkin.
- Profil to'ldirilgach, "tasdiqlanmagan" holatda qoladi (haqiqiy shifokor ekani hali tekshirilmagan).
  Tasdiqlash hozircha qo'lda (admin panelida ro'yxatni ko'rib, "tasdiqlash" tugmasi) — avtomatik
  diplom tekshirish keyingi bosqich, hozir yo'q.
- Tasdiqlanmagan shifokor ilovadan **foydalana oladi** (demo/sinov maqsadida), lekin bemorlarga va
  boshqa shifokorlarga "tasdiqlanmagan" belgisi bilan ko'rinadi, va Modul G (konsultatsiya)da
  unga so'rov yubormaydi — faqat tasdiqlangan shifokorlar konsultatsiyaga chiqadi.

### Tayyor bo'lish mezoni
Yangi shifokor to'liq profilni to'ldirmasdan tizimning qolgan qismiga (mijoz qo'shish va h.k.)
o'ta olmaydi. Hujjat fayllari yuklanadi va ko'rinadi. Admin tasdiqlash oqimi ishlaydi.

---

## 5. Modul C — Doktor tomonidan bemor qo'shish va taklif kodi

### Muammo
Ko'p bemorlar (ayniqsa yoshi kattaroq) o'zi telefon orqali ro'yxatdan o'tishda qiynaladi. Shifokor
buni o'zi bajarib, bemorga faqat bitta kod berishi kerak.

### Talab
Shifokor panelida "Mijoz qo'shish" bo'limi:

1. Shifokor bosadi → forma ochiladi: ism-familiya, telefon, tashxis (matn) + tashxisga tegishli
   fayl(lar) — rasm yoki PDF (bir nechta bo'lishi mumkin).
2. Yuborilgach, tizim **bitta, bir martalik, shu bemorga oldindan bog'langan** kod generatsiya qiladi
   (masalan 6-8 belgili, oson diktovka qilinadigan — harflar/raqamlar aralash emas, chalkash
   belgilarsiz: 0/O, 1/I kabi).
3. Shifokor bu kodni bemorga og'zaki yoki qog'ozda beradi (SMS/ilova orqali yuborish — keyingi
   bosqich, hozir shart emas).
4. Bemor (hali hisobi yo'q) ilovani ochadi → Google yoki Telegram orqali kiradi → "Doktor kodim bor"
   deb kodni kiritadi → tizim kodni kod bazasidan topadi, ishlatilmaganini tekshiradi, va shu
   bemorga tayyorlangan barcha ma'lumotni (ism, telefon, tashxis, fayllar) **avtomatik o'z
   profiliga ko'chiradi** — bemor hech narsani qayta kiritmaydi. Kod endi ishlatilgan deb belgilanadi.
5. Agar kod noto'g'ri, eskirgan yoki allaqachon ishlatilgan bo'lsa — tushunarli xabar, qayta urinish
   imkoni.

### Tayyor bo'lish mezoni
Shifokor bemor qo'shadi → kod oladi → boshqa (test) hisobdan shu kodni kiritadi → bemorning
profilida ism, telefon, tashxis va fayllar aynan shifokor kiritgandek ko'rinadi, ikkinchi marta
kiritilmaydi.

---

## 6. Modul D — Bemorning o'zi ro'yxatdan o'tishi va keyinroq shifokorga ulanishi

### Muammo
Har bir bemor ham shifokor orqali kelavermaydi — ba'zilar to'g'ridan-to'g'ri ilovani topib, o'zi
boshlashi kerak.

### Talab
- Bemor Google/Telegram orqali kirib, "bemor" rolini tanlaydi (yoki taklif kodisiz shunchaki
  davom etadi).
- Modul C'da shifokor to'ldiradigan xuddi shu ma'lumotlarni (ism, telefon, dori tartibi, tashxis —
  Modul E'ga qara) **endi bemorning o'zi** to'ldiradi.
- Bemor profilida alohida "Shifokorga ulanish" bo'limi bo'ladi: bu yerga shifokorning **umumiy
  ulanish kodi**ni kiritadi (Modul C'dagi bir martalik kod bilan chalkashtirmaslik kerak — bu
  boshqa turdagi kod, chunki bu holatda prefill kerak emas, faqat bog'lash kerak).
- Har bir shifokor o'z profilida shu umumiy kodni ko'radi (istalgan sonli bemor ishlatishi mumkin,
  vaqti-vaqti bilan yangilanishi mumkin — masalan xavfsizlik uchun).
- Kod kiritilgach, bemorning **mavjud** ma'lumotlari (u o'zi kiritgan dori/tashxis) o'zgarmaydi,
  faqat endi shu shifokorga ko'rinadigan bo'ladi va shifokor uni tahrirlashi mumkin bo'ladi.
- Bemor istalgan payt shifokorni o'zgartirishi/uzishi mumkin bo'lsin (ulanishni bekor qilish) —
  tarixiy ma'lumot yo'qolmaydi, faqat ko'rinish huquqi o'zgaradi.

### Tayyor bo'lish mezoni
Bemor shifokorsiz to'liq ro'yxatdan o'tadi, keyin kod orqali shifokorga ulanadi, shifokor uni
o'z ro'yxatida ko'radi va tahrirlay oladi.

---

## 7. Modul E — Dori tartibi va tashxis boshqaruvi (ikki tomonlama)

### Muammo
Modul C va D'da tavsiya qilingan "dori tartibi" va "tashxis" aslida bitta umumiy tizim — kim
kiritishidan qat'iy nazar (shifokor yoki bemorning o'zi), ma'lumot bir xil joyda saqlanishi va
**ikkala tomon ham** tahrirlay olishi kerak.

### Talab

**Dori tartibi:**
- Dori nomi, dozasi, ichish vaqtlari (kuniga necha mahal, qaysi soatlarda), boshlanish/tugash
  sanasi, faol/faol emas holati.
- Shifokor kiritishi, o'zgartirishi, to'xtatishi mumkin.
- Bemor ham o'zi kiritishi mumkin (Modul D holatida), lekin shifokorga ulangach, shifokor buni
  ko'rib, kerak bo'lsa tahrirlaydi/tasdiqlaydi.
- Dori vaqti kelganda bemorga eslatma — mavjud push/notifier tizimidan foydalaniladi, yangi kanal
  kerak emas.

**Tashxis:**
- Matn (tashxis nomi/tavsifi), holati (faol/yopilgan), va unga tegishli fayllar (rasm, PDF —
  bir nechta).
- Shifokor tashxisni yangilay oladi (masalan davolash borishiga qarab).
- Fayllar hozircha **faqat saqlanadi va ko'rsatiladi** — hech qanday avtomatik tahlil qilinmaydi.
  Lekin har fayl yozuvida "tahlil qilingan/qilinmagan" belgisi bo'lsin — bu keyinchalik AI
  tahlilchisi ulanganda (alohida, yangi kengaytma sifatida) qaysi fayllar hali ko'rib chiqilmaganini
  bilish uchun kerak. AI tahlilining o'zini hozir yozma.

**Umumiy qoida:** kim yozgani (shifokor yoki bemor) yozuvda saqlanadi (audit uchun), lekin bu
tahrirlash huquqini cheklamaydi — ikkala tomon ham bir-birining kiritganini ko'rib, to'g'irlashi
mumkin bo'lsin.

### Tayyor bo'lish mezoni
Shifokor dori qo'shsa — bemor chatida ko'rinadi va eslatma keladi. Bemor o'zi dori kiritsa —
shifokor panelida ko'rinadi va tahrirlanadi. Fayl yuklash ikkala tomondan ham ishlaydi.

---

## 8. Modul F — Trend grafik va motivatsiya

### Muammo
Hozir tendensiya faqat shifokor panelida bor (agar bor bo'lsa). Bemorning o'zi o'z holatini
vizual ko'rmaydi, va tizim faqat ogohlantiradi, hech qachon rag'batlantirmaydi.

### Talab
- Bemor o'z check-in ko'rsatkichlarini (mavjud tahlilchilardan chiqadigan qiymatlar) vaqt bo'yicha
  grafikda ko'rsin — mavjud xavf-rang tizimi (yashil/sariq/qizil) bilan mos.
- Motivatsiya manbalari **ikkitadan** keladi: (1) check-in tendensiyasi yaxshilanishi/yomonlashishi,
  (2) shifokor dori/tashxisni yangilaganda (masalan dozani to'g'rilagach, keyingi ko'rsatkichlar
  yaxshilansa — buni alohida ta'kidlash).
- Motivatsiya xabari qisqa, shaxsiylashtirilgan, o'zbek tilida bo'lsin, va **haddan tashqari tez-tez
  yubormasin** — masalan kuniga bittadan ortiq emas, va faqat haqiqiy o'zgarish bo'lganda (doim
  bir xil umumiy gap emas).
- Bu alohida, yangi tahlil turi sifatida qo'shiladi — mavjud xavf-tahlil (rule/LLM analyzer)
  pipeline'iga aralashtirilmaydi, chunki maqsadi boshqa (xavfni aniqlash emas, rag'batlantirish).

### Tayyor bo'lish mezoni
Bemor grafikni ko'radi. Ko'rsatkich yaxshilansa yoki shifokor dorini o'zgartirib natija yaxshi
chiqsa, bemorga tabriqlovchi/rag'batlantiruvchi xabar keladi — spam bo'lmagan holda.

---

## 9. Modul G — Bir martalik "Doktordan maslahat olish"

### Muammo
Ba'zi bemorlarga doimiy shifokorga bog'lanmasdan, faqat bitta savol uchun tez maslahat kerak
bo'ladi — va bu maslahat aynan shu bemorning tashxisi/dorilarini bilgan holda berilishi kerak,
bemor hammasini qayta yozib o'tirmasin.

### Talab

**Bemor tomonida:**
- "Maslahat so'rash" bo'limi: savol matni + kerakli soha/mutaxassislik tanlanadi (Modul B'dagi
  shifokor mutaxassisliklari ro'yxatidan).
- Yuborilganda, tizim bemorning **shu paytdagi** tashxis(lar)i, faol dorilari va profilini avtomatik
  "surat" qilib savolga bog'laydi — bemor bularni qayta kiritmaydi.
- Bu **bir martalik** — javob kelgach, bog'lanish tugaydi. Bemor bilan shifokor o'rtasida doimiy
  chat ochilmaydi (bu doimiy davolovchi shifokor bilan bo'ladigan alohida narsa).

**Shifokor tomonida:**
- Har shifokor o'z profilida "Konsultatsiyaga tayyorman" tumblerini yoqadi (soha bo'yicha).
- Faqat **tasdiqlangan** (Modul B) va shu soha bo'yicha tumblerini yoqqan, **hozir onlayn/mavjud**
  shifokorlarga so'rov ko'rinadi (push orqali xabar).
- Bir nechta shifokorga bir vaqtda ko'rinishi mumkin, lekin **birinchi bo'lib "qabul qilaman"
  bosgan shifokor** so'rovni oladi — qolganlarga endi ko'rinmaydi (ikki shifokor bitta savolni
  bir vaqtda ololmasin).
- Shifokor bemorning to'liq "surat"ini (tashxis, dorilar, savol) ko'radi, javob yozadi.
- Javob bemorga ilovada ko'rinadi (mavjud in-app/push notifier orqali).

### Tayyor bo'lish mezoni
Bemor savol yuborganda tegishli sohadagi mavjud shifokorlarga xabar boradi, biri qabul qilib
javob yozadi, bemor javobni oladi, bog'lanish shu bilan tugaydi (keyingi savol yana yangi
so'rov bo'ladi, xohlasa boshqa shifokorga tushishi mumkin).

---

## 10. Barcha modullar uchun umumiy talablar

- **Maxfiylik:** tibbiy ma'lumot (tashxis, dori, fayllar) faqat (a) bemorning o'zi, (b) unga
  bog'langan/ulangan shifokor(lar), (c) konsultatsiya holida — faqat o'sha aniq so'rovni qabul
  qilgan shifokorga ko'rinsin. Boshqa hech kim (masalan boshqa shifokorlar) ko'rmasin.
- **Fayl xavfsizligi:** yuklangan rasm/PDF'lar to'g'ridan-to'g'ri ochiq URL orqali emas, ruxsat
  tekshiruvidan o'tgan holda beriladi.
- **Har modul tugagach:** ilovani ishga tushir, tegishli oqimni qo'lda (yoki test yozib) sina,
  `pytest` ishlat, natijani ko'rsat — `CLAUDE.md`dagi qoidaga muvofiq. Ishlamagan narsani
  "ishlaydi" deb da'vo qilma.
- Har modul feature flag orqali yoqilib-o'chirilishi kerak (masalan `FEATURE_CONSULTATION`,
  `FEATURE_PATIENT_SELF_SIGNUP`) — shunda yarim tayyor funksiya demo paytida tasodifan ko'rinib
  qolmaydi.
- Har modul tugagach, agar arxitekturaga muhim qaror qo'shilgan bo'lsa (masalan yangi kengaytma
  nuqtasi turi), buni `PLAN.md`ga qisqa qo'shimcha sifatida yoz — hujjat eskirmasin.

---

## 11. Nima ishlamaydi hozircha (ataylab qoldirilgan)

Bularni **qurma**, faqat ular uchun joy qoldir (masalan bo'sh interfeys, o'chirilgan feature flag,
yoki bazada bitta bo'sh ustun):

- dmed bilan haqiqiy integratsiya (faqat provayder interfeysi bo'sh holatda).
- Diplom/hujjatlarni avtomatik tekshirish (hozir qo'lda tasdiqlash).
- Rasm/PDF'larni AI orqali avtomatik tahlil qilish (hozir faqat saqlash + "tahlil qilinmagan" belgisi).
- SMS orqali taklif kodini yuborish (hozir faqat kodni ko'rsatish, shifokor o'zi yetkazadi).
- Video/ovozli konsultatsiya (hozir faqat matnli savol-javob).
- Bir nechta hisobni birlashtirish (bir odam Google va Telegram bilan alohida ikki hisob ochsa,
  hozircha ikkita alohida hisob bo'lib qoladi).

---

## 12. Savolingiz bo'lsa

Agar biror joyda talab noaniq yoki ikki xil talqin qilinadigan bo'lsa (masalan taklif kodining
uzunligi, konsultatsiya so'rovining necha soat "ochiq" turishi, va h.k.) — o'zing oqilona qaror
qabul qil, uni qisqa izoh sifatida commit xabarida yoki `PLAN.md`da belgilab qo'y, va davom et.
Faqat arxitekturaga tub o'zgarish kiritadigan (masalan butun auth qatlamini boshqacha loyihalash)
noaniqlik bo'lsa — to'xtab so'ra.
