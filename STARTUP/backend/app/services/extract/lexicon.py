"""Label vocabulary for Uzbek (Latin + Cyrillic) and Russian documents.

Every label a vendor might print for a given field, in every script. This file
is the product's accumulated domain knowledge and is expected to grow with each
new invoice format encountered in production — adding a synonym here is the
cheapest possible accuracy fix, and needs no retraining.

Labels are matched after `script_detect.normalize_uzbek_latin` folding and
case-folding, so `Yetkazib beruvchi`, `YETKAZIB BERUVCHI` and `Yetkazib
beruvchi` all match one entry.
"""

from __future__ import annotations

# --- Document type detection ------------------------------------------------

DOCUMENT_TYPE_MARKERS: dict[str, tuple[str, ...]] = {
    "invoice": (
        "hisob-faktura", "hisob faktura", "schyot-faktura", "schot-faktura",
        "счет-фактура", "счёт-фактура", "счет фактура", "ҳисоб-фактура",
        "хисоб-фактура", "invoice", "schyot faktura",
    ),
    "waybill": (
        "yuk xati", "ttn", "tovar-transport", "товарно-транспортная",
        "накладная", "yuk-transport", "юк хати",
    ),
    "contract": ("shartnoma", "договор", "контракт", "шартнома"),
    "tax_form": ("soliq hisoboti", "налоговая отчетность", "деклараци"),
    "bank_statement": ("bank ko'chirmasi", "выписка", "банк кўчирмаси"),
}

# --- Field labels -----------------------------------------------------------

INVOICE_NUMBER_LABELS = (
    "hisob-faktura", "hisob faktura", "schyot-faktura", "faktura raqami",
    "hujjat raqami", "raqam", "raqami",
    "счет-фактура", "счёт-фактура", "счет фактура", "номер документа",
    "номер счета", "номер счёта", "фактура №", "номер", "ном",
    "ҳисоб-фактура", "хисоб-фактура", "рақами", "рақам", "ракам", "раками",
    "ҳужжат рақами", "фактура рақами",
)

DATE_LABELS = (
    "sana", "sanasi", "tuzilgan sana", "berilgan sana",
    "дата", "дата составления", "от", "сана", "санаси",
)

VENDOR_LABELS = (
    "yetkazib beruvchi", "etkazib beruvchi", "sotuvchi", "ta'minotchi",
    "taminotchi", "yuboruvchi",
    "поставщик", "продавец", "исполнитель", "грузоотправитель",
    "етказиб берувчи", "сотувчи", "таъминотчи",
)

BUYER_LABELS = (
    "xaridor", "haridor", "sotib oluvchi", "buyurtmachi", "qabul qiluvchi",
    "покупатель", "получатель", "заказчик", "грузополучатель", "плательщик",
    "харидор", "сотиб олувчи", "буюртмачи",
)

TIN_LABELS = (
    "stir", "s.t.i.r", "inn", "i.n.n", "стир", "инн", "и.н.н",
    "soliq to'lovchi", "soliq tolovchi", "идентификационный номер",
)

ADDRESS_LABELS = (
    "manzil", "manzili", "yuridik manzil", "pochta manzili",
    "адрес", "юридический адрес", "почтовый адрес", "манзил", "манзили",
)

CONTRACT_LABELS = (
    "shartnoma", "shartnoma raqami", "shartnoma bo'yicha",
    "договор", "договор №", "по договору", "контракт", "шартнома",
)

BANK_ACCOUNT_LABELS = (
    "hisob raqami", "h/r", "x/r", "bank hisob",
    "расчетный счет", "расчётный счет", "р/с", "р/сч", "банковский счет",
    "ҳисоб рақами",
)

# Grand total *including* VAT — what actually gets posted to 1C.
# Note the Uzbek Cyrillic spelling is ҚҚС (U+049A QA), not КҚС with a Russian К.
TOTAL_WITH_VAT_LABELS = (
    "jami qqs bilan", "qqs bilan jami", "hammasi qqs bilan", "jami (qqs bilan)",
    "to'lash uchun jami", "tolash uchun", "umumiy summa", "jami to'lovga",
    "всего к оплате", "итого к оплате", "всего с ндс", "итого с ндс",
    "всего с учетом ндс", "сумма к оплате",
    "жами ққс билан", "ққс билан жами", "жами (ққс билан)", "тўлаш учун жами",
)

# Net total *excluding* VAT.
SUBTOTAL_LABELS = (
    "jami", "jami summa", "qqssiz jami", "jami (qqssiz)", "summa jami",
    "итого", "всего", "сумма без ндс", "итого без ндс", "жами",
)

VAT_LABELS = (
    "qqs", "q.q.s", "qo'shilgan qiymat solig'i", "qqs summasi",
    "ндс", "н.д.с", "налог на добавленную стоимость", "сумма ндс",
    "ққс", "ққс суммаси", "қўшилган қиймат солиғи",
)

CURRENCY_LABELS = ("valyuta", "валюта", "valyutasi")

# --- Line-item table columns ------------------------------------------------

COLUMN_LABELS: dict[str, tuple[str, ...]] = {
    "index": ("№", "no", "n", "т/р", "т.р", "tartib", "тартиб", "п/п"),
    "description": (
        "tovar", "tovar nomi", "tovar (xizmat) nomi", "mahsulot nomi", "nomi",
        "xizmat", "xizmat nomi", "tavsif",
        "наименование", "наименование товара", "товар", "услуга", "описание",
        "товар (услуга)", "махсулот номи", "номи",
    ),
    "unit": (
        "o'lchov birligi", "olchov birligi", "birlik", "o'lchov",
        "ед.изм", "ед. изм", "единица измерения", "ед", "ўлчов бирлиги",
    ),
    "quantity": (
        "soni", "miqdori", "miqdor", "количество", "кол-во", "кол.", "сони",
        "миқдори",
    ),
    "unit_price": (
        "narxi", "narx", "bahosi", "цена", "цена за единицу", "нархи", "баҳоси",
    ),
    "amount": (
        "summa", "summasi", "qiymati", "сумма", "стоимость", "суммаси",
    ),
    "vat_rate": ("qqs stavkasi", "qqs %", "ставка ндс", "ндс %", "ққс ставкаси"),
    "vat_amount": ("qqs summasi", "сумма ндс", "ққс суммаси"),
}

# --- Units of measure -------------------------------------------------------

UNIT_TOKENS = (
    "dona", "kg", "tonna", "litr", "metr", "m2", "m3", "quti", "to'plam",
    "soat", "kun", "oy", "xizmat", "komplekt", "paket", "rulon",
    "шт", "кг", "тонна", "литр", "метр", "м2", "м3", "коробка", "компл",
    "час", "день", "месяц", "услуга", "упак", "рулон", "дона",
)

# Legal-form tokens that identify a counterparty name line even without a label.
LEGAL_FORMS = (
    "mchj", "m.ch.j", "aj", "a.j", "yatt", "qk", "xk", "ok", "dk", "xt",
    "ооо", "оао", "зао", "ао", "ип", "чп", "гуп", "муп", "нп", "мчж",
)


def all_labels() -> dict[str, tuple[str, ...]]:
    """Field name to label variants, for the generic label scanner."""
    return {
        "invoice_number": INVOICE_NUMBER_LABELS,
        "invoice_date": DATE_LABELS,
        "vendor_name": VENDOR_LABELS,
        "buyer_name": BUYER_LABELS,
        "vendor_tin": TIN_LABELS,
        "address": ADDRESS_LABELS,
        "contract_number": CONTRACT_LABELS,
        "total_with_vat": TOTAL_WITH_VAT_LABELS,
        "subtotal": SUBTOTAL_LABELS,
        "vat_amount": VAT_LABELS,
        "currency": CURRENCY_LABELS,
    }
