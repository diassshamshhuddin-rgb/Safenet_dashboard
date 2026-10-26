"""
Генератор синтетического датасета для хакатона SafeNet KZ.
Создает реалистичные данные по трем целевым трекам и трудным негативам на казахском,
русском, смешанном языках и транслите. Генерирует фиктивные скриншоты для OCR.
"""

import os
import json
import random
from pathlib import Path
from typing import List, Dict, Any, Tuple
from PIL import Image, ImageDraw, PngImagePlugin


SEED = 42
random.seed(SEED)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "synthetic"
IMAGES_DIR = DATA_DIR / "images"


# --- ШАБЛОНЫ И СЛОВАРИ ДЛЯ ГЕНЕРАЦИИ ---

LOTTERY_TEMPLATES_RU = [
    "🔥 МЕГА-РОЗЫГРЫШ IPHONE 16 PRO! Всего 100 номерков. Цена одного билета: {price} тенге. Перевод на Kaspi {phone}. Выбор через рандомайзер в прямом эфире в воскресенье!",
    "Участвуй в розыгрыше автомобиля Hyundai Elantra! Взнос за участие всего {price} тг. Оплата на карту {card}. Победитель определится через колесо фортуны в инсте!",
    "Срочный розыгрыш 500 000 тенге! Свободно только {slots} слотов. Бронь места после перевода {price} kzt на Kaspi Gold. Крутим барабан в эфире!",
    "Лотерея! Покупай билетики от {price} тг. Чем больше номеров берешь, тем выше шанс. Жеребьевка в субботу вечером в лайве!",
    "Авто-лотерея за копейки! Билет {price} тенге на Kaspi. Сбор открыт до заполнения всех 200 мест. В прямом эфире запустим рандом!"
]

LOTTERY_TEMPLATES_KK = [
    "🔥 IPHONE 16 ОЙНАТАМЫЗ! Бар болғаны 100 билет. Билет бағасы: {price} тг. Каспиге аудару: {phone}. Жеребе тікелей эфирде рандомайзер арқылы өтеді!",
    "Көлік ұтып ал! Қатысу жарнасы {price} теңге. Картаға аударым {card}. Жеңімпазды инстаграмда дөңгелек айналдыру арқылы таңдаймыз!",
    "Шұғыл ұтыс ойыны: 1 000 000 теңге! Орын саны шектеулі: {slots} орын қалды. Билет құны {price} тг Каспи голдқа жіберіңіз. Тікелей эфирде анықтаймыз!",
    "Лото ойыны! {price} теңгеден билет алып, ақшалай сыйлық ұтып алыңыз. Көп билет — көп мүмкіндік. Жеребе осы демалыста!",
    "Бар болғаны {price} тг салып жаңа телефон ұтып ал! Kaspi-ге аударып чек жіберіңіз. Тікелей эфирде лототронмен таңдаймыз!"
]

LOTTERY_TEMPLATES_TRANSLIT_MIXED = [
    "Mega utys oyyny! 1 bilet bagasy bar bolgany {price} tg. Kaspi arkyly audarynyz {phone}. Tikeli efirde randomaizer arkyly tandaimyz!",
    "Utyzga katysu ushin vznos {price} tenge. Kaspi gold nomerine audaryp, skrin zhiberiniz. Koleso fortuny ainaldyramyz!",
    "Розыгрышқа қатыс! 1 билет {price} тенге перевод на каспи. Randomizer арқылы тікелей эфирде таңдаймыз!",
    "Super bilet {price} kzt. 50 oryn kaldy. Efirde utys bolady, zherebe arkyly!"
]

CASINO_TEMPLATES_RU = [
    "🎰 Ребята, поднял за вечер {win_sum} тенге в слотах! Схема реально работает, вывод на Kaspi моментальный. Ссылка на зеркало в шапке профиля, промокод на +500%: {promo}",
    "Мой занос х1000 на Sweet Bonanza! Закинул 2000, вывел {win_sum} тг. К@зино платит без верификации. Рабочая ссылка: https://{domain}/reg?ref={promo}",
    "Кто хотел легких денег? Сегодня бонус 200 фриспинов всем новичкам. Переходи по ссылке в закрепе {domain}, вводи промокод {promo} и забирай куш!",
    "Стрим онлайн! Крутим слоты, раздаем ваучеры и промокоды. Ссылка на официальное зеркало: https://{domain}/play. Занос гарантирован!",
    "Скрины выплат за сегодня! Снова сорвал куш {win_sum} тг. Пока тему не прикрыли, регайтесь тут: https://{domain}/click?aff={promo}"
]

CASINO_TEMPLATES_KK = [
    "🎰 Бүгін тағы слотка 5000 салып, {win_sum} теңге ұтып алдым! Каспиге лезде түсті. Жұмыс істеп тұрған айна (зеркало) сілтемесі профильде, промокод: {promo}",
    "Слоттан оңай ақша тапқың келсе, мына сайтқа кір: https://{domain}. Тіркелгенде {promo} кодын жазсаң +300% бонус береді!",
    "Бүгінгі ұтысым! {win_sum} тг шығарып алдым. Ешқандай алдаусыз бірден Kaspi-ге түседі. Сілтеме шапкада, промокодты ұмытпаңыз!",
    "Стрим басталды! Ойындарды бірге ойнап, ақша табамыз. Тіркелу үшін сілтеме: https://{domain}/go, бонус промокод {promo}!"
]

CASINO_TEMPLATES_TRANSLIT_MIXED = [
    "Bugin kaz1noda {win_sum} tg uttym! Silteme zakrepte tur: https://{domain}. Promokod {promo} zhazyp bonus al!",
    "Slot arkyly tez aksha zhasau. Vyzvod kaspi-ge keldi {win_sum} kzt. Silteme profile-de: https://{domain}/bonus",
    "К@зuнодан бүгін {win_sum} тг түсті! Ссылка профильде, промокод {promo}. Қапы қалмаңыздар!"
]

PYRAMID_TEMPLATES_RU = [
    "💰 ПАССИВНЫЙ ДОХОД БЕЗ РИСКОВ! Вложи {invest_sum} тенге — забери {return_sum} тенге уже завтра! Гарантия 100%. Осталось всего {slots} мест в нашей VIP-группе! Пиши куратору.",
    "Касса взаимопомощи! Инвестируй {invest_sum} тг на Kaspi {phone}, получай выплату каждый день. За каждого приглашенного друга бонус +5000 тенге! Успей зайти на старте проекта!",
    "Хватит работать на дядю! Умножаем ваши вложения в 3 раза за 48 часов. Переводите на карту куратора {card}, выплаты идут нон-stop. Скриншоты довольных вкладчиков ниже!",
    "Закрытый инвестиционный пул в Telegram! Вход от {invest_sum} тг. Гарантированная выплата {return_sum} тенге. Срочно, места тают на глазах! Напишите менеджеру прямо сейчас.",
    "Отчет за сегодня: выплачено более 2 000 000 тг! Наш фонд гарантирует прибыль 50% в день. Перевод Kaspi {phone}. Реферальная программа 3 уровня!"
]

PYRAMID_TEMPLATES_KK = [
    "💰 АҚШАНЫ КӨБЕЙТУ! {invest_sum} теңге салсаңыз, 24 сағатта {return_sum} теңге аласыз! 100% кепілдік. Бар болғаны {slots} орын қалды! Кураторға жазыңыз.",
    "Өзара көмек кассасы! Каспиге {invest_sum} тг аударып {phone}, күн сайын табыс алыңыз. Досыңды шақырсаң үстінен 5000 тг сыйақы! Топқа тез қосылыңыз!",
    "Ақшаны 2 еселеу бағдарламасы! Бүгін салсаңыз ертең есепшотқа {return_sum} тг түседі. Чектер мен пікірлер каналда. Картаға аудару: {card}.",
    "Инвестициялық жоба! Ең аз салым {invest_sum} тг. Кепілдендірілген пайда. Орын саны шектеулі, қазір жазбасаңыз үлгермейсіз!"
]

PYRAMID_TEMPLATES_TRANSLIT_MIXED = [
    "Akshany kobeitu! {invest_sum} tg salyp {return_sum} tg alynyz. 100% kepildik bar. Kaspi arkyly audaru {phone}. Oryndar az kaldy!",
    "Bugin {invest_sum} kzt kospanyz, ertege {return_sum} kzt kaspige tusedi. Kuratorga zhazynyz, oryn sany: {slots} oryn!",
    "Инвестиция в Telegram! Салымыңыз {invest_sum} тг болса, пайдасы {return_sum} тг. Kaspi перевод, реферальный бонус!"
]

BENIGN_TEMPLATES_RU = [
    "🎁 БЕСПЛАТНЫЙ КОНКУРС в честь юбилея магазина! Условия простые: подпишись на нас, поставь лайк и отметь 2 друзей в комментариях. Участие абсолютно БЕСПЛАТНОЕ, никаких взносов и оплат! Итоги подведем в прямом эфире с помощью честного генератора случайных чисел.",
    "⚠️ Внимание! Агентство по финансовому мониторингу РК (АФМ) предупреждает граждан об опасности финансовых пирамид и сомнительных инвестиционных схем в мессенджерах. Никогда не переводите личные средства незнакомым лицам, обещающим гарантированный сверхдоход.",
    "Благотворительный фонд 'Мейірім'. Сбор средств на лечение трехлетнего Алихана. Диагноз и все медицинские выписки прикреплены к публикации. Отчетность по каждой поступившей копейке публикуется на нашем официальном сайте. Реквизиты фонда: KZ123456789012345.",
    "Финансовая грамотность: почему депозиты надежнее сомнительных предложений. Казахстанский фонд гарантирования депозитов (КФГД) защищает сбережения граждан до 20 млн тенге. Ставки вознаграждения в банках достигают 14.5% годовых.",
    "Реклама официального ритейлера техники: Скидки до 40% на смартфоны и ноутбуки ко Дню Республики! Официальная гарантия 1 год. Рассрочка 0-0-24 в ведущих банках Казахстана.",
    "Киберспорт в Казахстане: открыта регистрация на открытый студенческий турнир по CS2 и Dota 2. Участие команд бесплатное, призовой фонд предоставлен спонсорами."
]

BENIGN_TEMPLATES_KK = [
    "🎁 ДҮКЕННІҢ ТУҒАН КҮНІНЕ ТЕГІН КОНКУРС! Шарттары өте қарапайым: парақшаға жазылыңыз, лайк басыңыз және пікірге 2 досыңызды белгілеңіз. Қатысу МҮЛДЕМ ТЕГІН, ешқандай төлем немесе жарна жоқ! Жеңімпазды тікелей эфирде анықтаймыз.",
    "⚠️ Қаржылық мониторинг агенттігі (ҚМА) азаматтарды әлеуметтік желілердегі қаржылық пирамидалардан сақ болуға шақырады. Жылдам пайда табуды уәде ететін күмәнді тұлғаларға ақша аудармаңыздар.",
    "Қайырымдылық қоры: кішкентай Айсұлтанның еміне қаражат жинауға қолдау көрсетіңіз. Барлық ресми медициналық құжаттар мен есептер ресми сайтымызда жарияланған.",
    "Қаржылық сауаттылық: ақшаны қалай дұрыс сақтау керек? Екінші деңгейлі банктердегі депозиттер Қазақстанның депозиттерге кепілдік беру қорымен (ҚДКБҚ) 20 млн теңгеге дейін сақтандырылған.",
    "Тұрмыстық техника дүкенінен күзгі жеңілдіктер! Тек ресми тауарлар мен кепілдіктер. Kaspi Red және 0-0-24 бөліп төлеу қарастырылған."
]


def generate_synthetic_image(text: str, filename: str) -> str:
    """Генерирует тестовое изображение со скриншотом текста для OCR и сохраняет метаданные."""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    img_path = IMAGES_DIR / filename
    
    img = Image.new('RGB', (600, 260), color=(30, 33, 40))
    draw = ImageDraw.Draw(img)
    
    draw.rectangle([20, 20, 580, 240], fill=(45, 52, 64), outline=(70, 80, 95), width=2)
    
    lines = []
    words = text.split()
    current_line = []
    for word in words:
        current_line.append(word)
        if len(" ".join(current_line)) > 35:
            lines.append(" ".join(current_line))
            current_line = []
    if current_line:
        lines.append(" ".join(current_line))
        
    y = 40
    for line in lines[:5]:
        draw.text((40, y), line, fill=(240, 245, 255))
        y += 35
        
    # Сохраняем текстовую подсказку в PNG-метаданные
    meta = PngImagePlugin.PngInfo()
    meta.add_text("description", text)
    img.save(img_path, pnginfo=meta)
    
    # Также сохраняем sidecar-файл на случай работы без Tesseract
    sidecar_path = IMAGES_DIR / f"{filename}.txt"
    with open(sidecar_path, "w", encoding="utf-8") as f:
        f.write(text)
        
    return str(img_path)


def generate_dataset(total_records: int = 1200) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    records = []
    count_per_category = total_records // 4
    
    synthetic_domains = ["win-kazakhstan.test", "lucky-slot777.test", "royal-spin.test", "bonus-asia.test", "spin-kz.test"]
    synthetic_promos = ["SAFEKZ", "WIN500", "ALMATY", "JETKZ", "BONUS100", "LUCKY2026"]
    
    ocr_img_1 = generate_synthetic_image("Вложи 10000 тг получи 25000 тг Kaspi +77019876543 гарантия", "ocr_pyramid_sample.png")
    ocr_img_2 = generate_synthetic_image("Мой занос х500 промокод SAFEKZ зеркало https://lucky-slot777.test", "ocr_casino_sample.png")
    ocr_img_3 = generate_synthetic_image("1 билет 1500 тг перевод на Kaspi розыгрыш авто в прямом эфире", "ocr_lottery_sample.png")
    ocr_img_4 = generate_synthetic_image("Конкурс! Участие бесплатное. Лайк и репост без взносов.", "ocr_benign_sample.png")
    
    idx = 1
    
    # 1. LOTTERY
    for _ in range(count_per_category):
        lang_choice = random.choice(["ru", "kk", "mixed_translit"])
        price = random.choice([500, 1000, 1500, 2000, 3000, 5000])
        slots = random.choice([3, 5, 10, 15, 20])
        phone = f"+770{random.randint(1000000, 9999999)}"
        card = f"4400 4301 {random.randint(1000, 9999)} {random.randint(1000, 9999)}"
        
        if lang_choice == "ru":
            tpl = random.choice(LOTTERY_TEMPLATES_RU)
        elif lang_choice == "kk":
            tpl = random.choice(LOTTERY_TEMPLATES_KK)
        else:
            tpl = random.choice(LOTTERY_TEMPLATES_TRANSLIT_MIXED)
            
        text = tpl.format(price=price, slots=slots, phone=phone, card=card)
        if random.random() < 0.25:
            text = text.replace("билет", "бuлет").replace("розыгрыш", "р0зыгрыш").replace("Каспи", "К@спи")
            
        images = [ocr_img_3] if idx % 50 == 0 else []
        records.append({
            "id": f"case_lottery_{idx:04d}",
            "text": text,
            "image_paths": images,
            "channel_or_account": f"@lottery_kz_{random.randint(1, 20)}",
            "platform": random.choice(["telegram", "instagram", "whatsapp", "tiktok"]),
            "track": "lottery",
            "label": "suspicious",
            "metadata": {"card": card if random.random() < 0.5 else None, "phone": phone},
            "synthetic": True
        })
        idx += 1

    # 2. CASINO
    for _ in range(count_per_category):
        lang_choice = random.choice(["ru", "kk", "mixed_translit"])
        win_sum = random.choice(["150 000", "280 000", "500 000", "1 200 000", "3 500 000"])
        domain = random.choice(synthetic_domains)
        promo = random.choice(synthetic_promos)
        
        if lang_choice == "ru":
            tpl = random.choice(CASINO_TEMPLATES_RU)
        elif lang_choice == "kk":
            tpl = random.choice(CASINO_TEMPLATES_KK)
        else:
            tpl = random.choice(CASINO_TEMPLATES_TRANSLIT_MIXED)
            
        text = tpl.format(win_sum=win_sum, domain=domain, promo=promo)
        if random.random() < 0.3:
            text = text.replace("казино", "к@зино").replace("слот", "сл0т").replace("бонус", "б0нус")
            
        images = [ocr_img_2] if idx % 50 == 0 else []
        records.append({
            "id": f"case_casino_{idx:04d}",
            "text": text,
            "image_paths": images,
            "channel_or_account": f"@streamer_{random.randint(1, 15)}",
            "platform": random.choice(["telegram", "instagram", "tiktok"]),
            "track": "casino",
            "label": "suspicious",
            "metadata": {"domain": domain, "promocode": promo},
            "synthetic": True
        })
        idx += 1

    # 3. PYRAMID
    for _ in range(count_per_category):
        lang_choice = random.choice(["ru", "kk", "mixed_translit"])
        invest_sum = random.choice(["3 000", "5 000", "10 000", "20 000", "50 000"])
        return_sum = random.choice(["10 000", "15 000", "30 000", "60 000", "150 000"])
        slots = random.choice([2, 3, 4, 5])
        phone = f"+770{random.randint(1000000, 9999999)}"
        card = f"5169 4931 {random.randint(1000, 9999)} {random.randint(1000, 9999)}"
        
        if lang_choice == "ru":
            tpl = random.choice(PYRAMID_TEMPLATES_RU)
        elif lang_choice == "kk":
            tpl = random.choice(PYRAMID_TEMPLATES_KK)
        else:
            tpl = random.choice(PYRAMID_TEMPLATES_TRANSLIT_MIXED)
            
        text = tpl.format(invest_sum=invest_sum, return_sum=return_sum, slots=slots, phone=phone, card=card)
        if random.random() < 0.3:
            text = text.replace("пирамида", "пuрамида").replace("вложи", "вл0жи").replace("доход", "д0ход")
            
        images = [ocr_img_1] if idx % 50 == 0 else []
        records.append({
            "id": f"case_pyramid_{idx:04d}",
            "text": text,
            "image_paths": images,
            "channel_or_account": f"@invest_group_{random.randint(1, 20)}",
            "platform": random.choice(["whatsapp", "telegram"]),
            "track": "pyramid",
            "label": "suspicious",
            "metadata": {"card": card, "phone": phone},
            "synthetic": True
        })
        idx += 1

    # 4. BENIGN
    remaining_benign = total_records - len(records)
    for _ in range(remaining_benign):
        lang_choice = random.choice(["ru", "kk"])
        if lang_choice == "ru":
            text = random.choice(BENIGN_TEMPLATES_RU)
        else:
            text = random.choice(BENIGN_TEMPLATES_KK)
            
        images = [ocr_img_4] if idx % 50 == 0 else []
        records.append({
            "id": f"case_benign_{idx:04d}",
            "text": text,
            "image_paths": images,
            "channel_or_account": f"@official_org_{random.randint(1, 15)}",
            "platform": random.choice(["telegram", "instagram", "whatsapp"]),
            "track": "benign",
            "label": "benign",
            "metadata": {},
            "synthetic": True
        })
        idx += 1

    random.shuffle(records)
    n_train = int(len(records) * 0.70)
    n_val = int(len(records) * 0.15)
    
    train_data = records[:n_train]
    val_data = records[n_train:n_train + n_val]
    test_data = records[n_train + n_val:]
    
    return train_data, val_data, test_data


def save_dataset_files(train: List[Dict], val: List[Dict], test: List[Dict], target_dir: Path = DATA_DIR):
    target_dir.mkdir(parents=True, exist_ok=True)
    for split_name, dataset in [("train", train), ("val", val), ("test", test)]:
        file_path = target_dir / f"{split_name}.jsonl"
        with open(file_path, "w", encoding="utf-8") as f:
            for item in dataset:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    train, val, test = generate_dataset(total_records=1200)
    save_dataset_files(train, val, test)