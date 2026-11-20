/**
 * Uzbek-first interface strings.
 *
 * The MVP spec is explicit: "Uzbek language interface (with Russian toggle).
 * No English." Chief accountants in this market read Uzbek Latin or Russian;
 * an English UI is an immediate disqualifier in a demo.
 *
 * Uzbek Cyrillic is included because a meaningful share of accountants over 40
 * still read it more comfortably than Latin — the same script transition that
 * creates the document problem this product solves.
 */

export type Locale = "uz" | "uz-Cyrl" | "ru";

export const LOCALES: { code: Locale; label: string }[] = [
  { code: "uz", label: "O'zbekcha" },
  { code: "uz-Cyrl", label: "Ўзбекча" },
  { code: "ru", label: "Русский" },
];

export const DEFAULT_LOCALE: Locale = "uz";

const dictionary = {
  appName: {
    uz: "HujjatAI",
    "uz-Cyrl": "HujjatAI",
    ru: "HujjatAI",
  },
  tagline: {
    uz: "Hisob-fakturalarni 1C ga soniyalarda o'tkazing",
    "uz-Cyrl": "Ҳисоб-фактураларни 1С га сонияларда ўтказинг",
    ru: "Переносите счета-фактуры в 1С за секунды",
  },

  // Navigation
  navDashboard: { uz: "Boshqaruv paneli", "uz-Cyrl": "Бошқарув панели", ru: "Панель управления" },
  navUpload: { uz: "Yuklash", "uz-Cyrl": "Юклаш", ru: "Загрузка" },
  navDocuments: { uz: "Hujjatlar", "uz-Cyrl": "Ҳужжатлар", ru: "Документы" },
  navSettings: { uz: "Sozlamalar", "uz-Cyrl": "Созламалар", ru: "Настройки" },
  logout: { uz: "Chiqish", "uz-Cyrl": "Чиқиш", ru: "Выйти" },

  // Auth
  login: { uz: "Kirish", "uz-Cyrl": "Кириш", ru: "Вход" },
  register: { uz: "Ro'yxatdan o'tish", "uz-Cyrl": "Рўйхатдан ўтиш", ru: "Регистрация" },
  email: { uz: "Elektron pochta", "uz-Cyrl": "Электрон почта", ru: "Электронная почта" },
  password: { uz: "Parol", "uz-Cyrl": "Парол", ru: "Пароль" },
  fullName: { uz: "To'liq ism", "uz-Cyrl": "Тўлиқ исм", ru: "Полное имя" },
  companyName: { uz: "Tashkilot nomi", "uz-Cyrl": "Ташкилот номи", ru: "Название организации" },
  companyTin: { uz: "Tashkilot STIR", "uz-Cyrl": "Ташкилот СТИР", ru: "ИНН организации" },
  noAccount: { uz: "Hisobingiz yo'qmi?", "uz-Cyrl": "Ҳисобингиз йўқми?", ru: "Нет аккаунта?" },
  haveAccount: { uz: "Hisobingiz bormi?", "uz-Cyrl": "Ҳисобингиз борми?", ru: "Уже есть аккаунт?" },

  // Dashboard
  documentsThisMonth: { uz: "Bu oyda hujjatlar", "uz-Cyrl": "Бу ойда ҳужжатлар", ru: "Документов за месяц" },
  timeSaved: { uz: "Tejalgan vaqt", "uz-Cyrl": "Тежалган вақт", ru: "Сэкономлено времени" },
  needsReview: { uz: "Tekshirish kerak", "uz-Cyrl": "Текшириш керак", ru: "Требует проверки" },
  averageAccuracy: { uz: "O'rtacha ishonch", "uz-Cyrl": "Ўртача ишонч", ru: "Средняя уверенность" },
  hours: { uz: "soat", "uz-Cyrl": "соат", ru: "часов" },
  minutes: { uz: "daqiqa", "uz-Cyrl": "дақиқа", ru: "минут" },
  knownVendors: { uz: "Tanilgan yetkazib beruvchilar", "uz-Cyrl": "Танилган етказиб берувчилар", ru: "Известные поставщики" },
  topVendors: { uz: "Asosiy yetkazib beruvchilar", "uz-Cyrl": "Асосий етказиб берувчилар", ru: "Основные поставщики" },
  quotaUsed: { uz: "Oylik limitdan foydalanilgan", "uz-Cyrl": "Ойлик лимитдан фойдаланилган", ru: "Использовано от лимита" },
  correctionRate: { uz: "Tuzatishlar ulushi", "uz-Cyrl": "Тузатишлар улуши", ru: "Доля исправлений" },
  noDataYet: { uz: "Hali ma'lumot yo'q", "uz-Cyrl": "Ҳали маълумот йўқ", ru: "Пока нет данных" },

  // Upload
  uploadTitle: { uz: "Hujjatlarni yuklash", "uz-Cyrl": "Ҳужжатларни юклаш", ru: "Загрузка документов" },
  dropFiles: {
    uz: "Fayllarni bu yerga tashlang yoki tanlash uchun bosing",
    "uz-Cyrl": "Файлларни бу ерга ташланг ёки танлаш учун босинг",
    ru: "Перетащите файлы сюда или нажмите для выбора",
  },
  uploadHint: {
    uz: "PDF, JPG, PNG yoki TIFF. Bir vaqtda 20 tagacha fayl, har biri 10 MB gacha.",
    "uz-Cyrl": "PDF, JPG, PNG ёки TIFF. Бир вақтда 20 тагача файл, ҳар бири 10 МБ гача.",
    ru: "PDF, JPG, PNG или TIFF. До 20 файлов за раз, каждый до 10 МБ.",
  },
  uploadButton: { uz: "Yuklash", "uz-Cyrl": "Юклаш", ru: "Загрузить" },
  uploading: { uz: "Yuklanmoqda...", "uz-Cyrl": "Юкланмоқда...", ru: "Загрузка..." },
  uploadAccepted: { uz: "Qabul qilindi", "uz-Cyrl": "Қабул қилинди", ru: "Принято" },
  uploadRejected: { uz: "Rad etildi", "uz-Cyrl": "Рад этилди", ru: "Отклонено" },
  selectedFiles: { uz: "Tanlangan fayllar", "uz-Cyrl": "Танланган файллар", ru: "Выбранные файлы" },

  // Documents
  documentsTitle: { uz: "Hujjatlar", "uz-Cyrl": "Ҳужжатлар", ru: "Документы" },
  fileName: { uz: "Fayl nomi", "uz-Cyrl": "Файл номи", ru: "Имя файла" },
  status: { uz: "Holati", "uz-Cyrl": "Ҳолати", ru: "Статус" },
  vendor: { uz: "Yetkazib beruvchi", "uz-Cyrl": "Етказиб берувчи", ru: "Поставщик" },
  amount: { uz: "Summa", "uz-Cyrl": "Сумма", ru: "Сумма" },
  uploadedAt: { uz: "Yuklangan vaqt", "uz-Cyrl": "Юкланган вақт", ru: "Дата загрузки" },
  allStatuses: { uz: "Barcha holatlar", "uz-Cyrl": "Барча ҳолатлар", ru: "Все статусы" },
  noDocuments: {
    uz: "Hali hujjat yo'q. Birinchi hisob-fakturangizni yuklang.",
    "uz-Cyrl": "Ҳали ҳужжат йўқ. Биринчи ҳисоб-фактурангизни юкланг.",
    ru: "Пока нет документов. Загрузите первую счёт-фактуру.",
  },
  exportSelected: { uz: "1C ga eksport", "uz-Cyrl": "1С га экспорт", ru: "Экспорт в 1С" },
  selected: { uz: "tanlandi", "uz-Cyrl": "танланди", ru: "выбрано" },
  refresh: { uz: "Yangilash", "uz-Cyrl": "Янгилаш", ru: "Обновить" },

  // Statuses
  statusPending: { uz: "Navbatda", "uz-Cyrl": "Навбатда", ru: "В очереди" },
  statusProcessing: { uz: "Ishlanmoqda", "uz-Cyrl": "Ишланмоқда", ru: "Обработка" },
  statusReady: { uz: "Tayyor", "uz-Cyrl": "Тайёр", ru: "Готово" },
  statusNeedsReview: { uz: "Tekshirish kerak", "uz-Cyrl": "Текшириш керак", ru: "Нужна проверка" },
  statusConfirmed: { uz: "Tasdiqlangan", "uz-Cyrl": "Тасдиқланган", ru: "Подтверждено" },
  statusFailed: { uz: "Xatolik", "uz-Cyrl": "Хатолик", ru: "Ошибка" },

  // Review
  reviewTitle: { uz: "Tekshirish va tuzatish", "uz-Cyrl": "Текшириш ва тузатиш", ru: "Проверка и исправление" },
  originalDocument: { uz: "Asl hujjat", "uz-Cyrl": "Асл ҳужжат", ru: "Оригинал документа" },
  extractedData: { uz: "Ajratilgan ma'lumotlar", "uz-Cyrl": "Ажратилган маълумотлар", ru: "Извлечённые данные" },
  lineItems: { uz: "Tovarlar va xizmatlar", "uz-Cyrl": "Товарлар ва хизматлар", ru: "Товары и услуги" },
  saveAndConfirm: { uz: "Saqlash va tasdiqlash", "uz-Cyrl": "Сақлаш ва тасдиқлаш", ru: "Сохранить и подтвердить" },
  saving: { uz: "Saqlanmoqda...", "uz-Cyrl": "Сақланмоқда...", ru: "Сохранение..." },
  exportTo1C: { uz: "1C ga yuklab olish", "uz-Cyrl": "1С га юклаб олиш", ru: "Скачать для 1С" },
  confidenceHigh: { uz: "Yuqori ishonch", "uz-Cyrl": "Юқори ишонч", ru: "Высокая уверенность" },
  confidenceMedium: { uz: "O'rtacha ishonch", "uz-Cyrl": "Ўртача ишонч", ru: "Средняя уверенность" },
  confidenceLow: { uz: "Past ishonch — tekshiring", "uz-Cyrl": "Паст ишонч — текширинг", ru: "Низкая уверенность — проверьте" },
  checkThis: { uz: "Tekshiring", "uz-Cyrl": "Текширинг", ru: "Проверьте" },
  problemsFound: { uz: "Topilgan muammolar", "uz-Cyrl": "Топилган муаммолар", ru: "Найденные проблемы" },
  weCorrected: {
    uz: "Yetkazib beruvchilar ro'yxatingiz bo'yicha tuzatildi",
    "uz-Cyrl": "Етказиб берувчилар рўйхатингиз бўйича тузатилди",
    ru: "Исправлено по вашему списку поставщиков",
  },
  processedIn: { uz: "Ishlash vaqti", "uz-Cyrl": "Ишлаш вақти", ru: "Время обработки" },
  scriptMix: { uz: "Yozuv turi", "uz-Cyrl": "Ёзув тури", ru: "Тип письма" },
  showOcrText: { uz: "OCR matnini ko'rsatish", "uz-Cyrl": "OCR матнини кўрсатиш", ru: "Показать текст OCR" },
  hideOcrText: { uz: "OCR matnini yashirish", "uz-Cyrl": "OCR матнини яшириш", ru: "Скрыть текст OCR" },
  reprocess: { uz: "Qayta ishlash", "uz-Cyrl": "Қайта ишлаш", ru: "Обработать заново" },

  // Field labels — these mirror what the accountant sees on the paper document
  invoice_number: { uz: "Hisob-faktura raqami", "uz-Cyrl": "Ҳисоб-фактура рақами", ru: "Номер счёта-фактуры" },
  invoice_date: { uz: "Sana", "uz-Cyrl": "Сана", ru: "Дата" },
  vendor_name: { uz: "Yetkazib beruvchi", "uz-Cyrl": "Етказиб берувчи", ru: "Поставщик" },
  vendor_tin: { uz: "Yetkazib beruvchi STIR", "uz-Cyrl": "Етказиб берувчи СТИР", ru: "ИНН поставщика" },
  vendor_address: { uz: "Yetkazib beruvchi manzili", "uz-Cyrl": "Етказиб берувчи манзили", ru: "Адрес поставщика" },
  buyer_name: { uz: "Xaridor", "uz-Cyrl": "Харидор", ru: "Покупатель" },
  buyer_tin: { uz: "Xaridor STIR", "uz-Cyrl": "Харидор СТИР", ru: "ИНН покупателя" },
  buyer_address: { uz: "Xaridor manzili", "uz-Cyrl": "Харидор манзили", ru: "Адрес покупателя" },
  contract_number: { uz: "Shartnoma raqami", "uz-Cyrl": "Шартнома рақами", ru: "Номер договора" },
  contract_date: { uz: "Shartnoma sanasi", "uz-Cyrl": "Шартнома санаси", ru: "Дата договора" },
  subtotal: { uz: "Jami (QQSsiz)", "uz-Cyrl": "Жами (ҚҚСсиз)", ru: "Итого без НДС" },
  vat_amount: { uz: "QQS summasi", "uz-Cyrl": "ҚҚС суммаси", ru: "Сумма НДС" },
  total_amount: { uz: "Jami QQS bilan", "uz-Cyrl": "Жами ҚҚС билан", ru: "Всего к оплате" },
  currency: { uz: "Valyuta", "uz-Cyrl": "Валюта", ru: "Валюта" },

  // Line-item columns
  colIndex: { uz: "№", "uz-Cyrl": "№", ru: "№" },
  colDescription: { uz: "Tovar (xizmat) nomi", "uz-Cyrl": "Товар (хизмат) номи", ru: "Наименование" },
  colUnit: { uz: "O'lchov", "uz-Cyrl": "Ўлчов", ru: "Ед.изм" },
  colQuantity: { uz: "Soni", "uz-Cyrl": "Сони", ru: "Кол-во" },
  colUnitPrice: { uz: "Narxi", "uz-Cyrl": "Нархи", ru: "Цена" },
  colAmount: { uz: "Summa", "uz-Cyrl": "Сумма", ru: "Сумма" },

  // Settings
  settingsTitle: { uz: "Sozlamalar", "uz-Cyrl": "Созламалар", ru: "Настройки" },
  companySettings: { uz: "Tashkilot ma'lumotlari", "uz-Cyrl": "Ташкилот маълумотлари", ru: "Данные организации" },
  onecSettings: { uz: "1C sozlamalari", "uz-Cyrl": "1С созламалари", ru: "Настройки 1С" },
  onecOrganization: { uz: "1C dagi tashkilot nomi", "uz-Cyrl": "1С даги ташкилот номи", ru: "Название организации в 1С" },
  onecOperation: { uz: "Hujjat turi", "uz-Cyrl": "Ҳужжат тури", ru: "Вид документа" },
  team: { uz: "Jamoa", "uz-Cyrl": "Жамоа", ru: "Команда" },
  save: { uz: "Saqlash", "uz-Cyrl": "Сақлаш", ru: "Сохранить" },
  saved: { uz: "Saqlandi", "uz-Cyrl": "Сақланди", ru: "Сохранено" },
  address: { uz: "Manzil", "uz-Cyrl": "Манзил", ru: "Адрес" },
  role: { uz: "Rol", "uz-Cyrl": "Рол", ru: "Роль" },
  interfaceLanguage: { uz: "Interfeys tili", "uz-Cyrl": "Интерфейс тили", ru: "Язык интерфейса" },

  // Generic
  loading: { uz: "Yuklanmoqda...", "uz-Cyrl": "Юкланмоқда...", ru: "Загрузка..." },
  error: { uz: "Xatolik", "uz-Cyrl": "Хатолик", ru: "Ошибка" },
  back: { uz: "Orqaga", "uz-Cyrl": "Орқага", ru: "Назад" },
  cancel: { uz: "Bekor qilish", "uz-Cyrl": "Бекор қилиш", ru: "Отмена" },
  retry: { uz: "Qayta urinish", "uz-Cyrl": "Қайта уриниш", ru: "Повторить" },
} as const;

export type TranslationKey = keyof typeof dictionary;

export function t(key: TranslationKey, locale: Locale): string {
  const entry = dictionary[key];
  if (!entry) return key;
  return entry[locale] ?? entry.uz;
}

const STATUS_KEYS: Record<string, TranslationKey> = {
  pending: "statusPending",
  processing: "statusProcessing",
  ready: "statusReady",
  needs_review: "statusNeedsReview",
  confirmed: "statusConfirmed",
  failed: "statusFailed",
};

export function translateStatus(status: string, locale: Locale): string {
  const key = STATUS_KEYS[status];
  return key ? t(key, locale) : status;
}
