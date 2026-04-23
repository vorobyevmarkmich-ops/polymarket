from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "MVP_0_SCREENER_CLIENT_PRESENTATION.pdf"

FONT_REGULAR = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

WIDTH = 13.333 * inch
HEIGHT = 7.5 * inch

BG = colors.HexColor("#071018")
PANEL = colors.HexColor("#0D1822")
PANEL_2 = colors.HexColor("#102333")
GREEN = colors.HexColor("#31D07A")
CYAN = colors.HexColor("#4CC9F0")
TEXT = colors.HexColor("#F3F7FA")
MUTED = colors.HexColor("#AAB6C2")
LINE = colors.HexColor("#203445")


SLIDES = [
    {
        "eyebrow": "MVP-0 / LIVE SCREENER",
        "title": "Real-time скринер Polymarket",
        "subtitle": "Бот 24/7 мониторит рынки, ищет потенциальные арбитражные окна и отправляет сигналы в Telegram.",
        "bullets": [
            "Запущен как Railway worker",
            "Проверяет до 1000 активных рынков",
            "Telegram-бот уже подключен",
        ],
        "metric": "24/7",
        "metric_label": "автоматический мониторинг",
    },
    {
        "eyebrow": "PROBLEM",
        "title": "Рынок движется быстрее ручного мониторинга",
        "subtitle": "Polymarket постоянно обновляет цены и добавляет новые рынки. Возможности живут коротко, а вручную отслеживать сотни событий невозможно.",
        "bullets": [
            "Много рынков и outcome-токенов",
            "Спреды быстро исчезают",
            "Нужна автоматическая проверка orderbook-данных",
        ],
        "metric": "1000+",
        "metric_label": "рынков в сканировании",
    },
    {
        "eyebrow": "HOW IT WORKS",
        "title": "Как работает MVP",
        "subtitle": "Система получает активные рынки, забирает ask-цены YES и NO, считает total cost и фильтрует только потенциально интересные ситуации.",
        "bullets": [
            "Discovery активных и новых рынков",
            "Формула: YES ask + NO ask < 1.00",
            "Cooldown защищает от Telegram-спама",
        ],
        "metric": "10 sec",
        "metric_label": "текущий scan interval",
    },
    {
        "eyebrow": "CLIENT VALUE",
        "title": "Что получает клиент",
        "subtitle": "Это не обещание доходности, а инструмент раннего обнаружения рыночных возможностей для трейдера или оператора.",
        "bullets": [
            "Сигналы приходят сразу в Telegram",
            "Можно проверять рынки быстрее конкурентов",
            "Собирается база для оценки стратегии и PnL",
        ],
        "metric": "Signal",
        "metric_label": "аналитика, не автотрейдинг",
    },
    {
        "eyebrow": "MONETIZATION",
        "title": "Как на этом зарабатывать",
        "subtitle": "MVP можно монетизировать как доступ к сигналам, аналитику или кастомный мониторинг для активных участников prediction markets.",
        "bullets": [
            "Подписка на приватные Telegram-сигналы",
            "Кастомные фильтры под рынки клиента",
            "Отчеты по частоте, размеру и качеству возможностей",
            "Следующий этап: controlled execution для операторов",
        ],
        "metric": "$",
        "metric_label": "модель подписки / аналитики",
    },
    {
        "eyebrow": "WHY NOW",
        "title": "Почему это безопасный первый шаг",
        "subtitle": "Мы не принимаем депозиты, не делаем выводы и не исполняем сделки автоматически. Сначала проверяем рынок и экономику сигналов.",
        "bullets": [
            "Нет custody-risk на MVP-0",
            "Нет публичного инвестиционного продукта",
            "Можно быстро валидировать гипотезу без тяжелой платформы",
        ],
        "metric": "0",
        "metric_label": "автоматических сделок",
    },
    {
        "eyebrow": "NEXT STEP",
        "title": "Что строим дальше",
        "subtitle": "Если сигналы покажут достаточную частоту и качество, следующий шаг — operator dashboard, история сигналов и PnL tracking после ручных сделок.",
        "bullets": [
            "История сигналов и качество исполнения",
            "Orderbook-based size estimation",
            "Operator dashboard",
            "Controlled execution после подтверждения экономики",
        ],
        "metric": "v1",
        "metric_label": "dashboard + PnL + execution controls",
    },
]


def register_fonts() -> None:
    pdfmetrics.registerFont(TTFont("DeckRegular", FONT_REGULAR))
    pdfmetrics.registerFont(TTFont("DeckBold", FONT_BOLD))


def text_lines(c: canvas.Canvas, text: str, x: float, y: float, max_width: float, font: str, size: int, leading: int, color) -> float:
    c.setFont(font, size)
    c.setFillColor(color)
    words = text.split()
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if c.stringWidth(candidate, font, size) <= max_width:
            line = candidate
        else:
            c.drawString(x, y, line)
            y -= leading
            line = word
    if line:
        c.drawString(x, y, line)
        y -= leading
    return y


def draw_background(c: canvas.Canvas, page_num: int) -> None:
    c.setFillColor(BG)
    c.rect(0, 0, WIDTH, HEIGHT, stroke=0, fill=1)

    c.setStrokeColor(colors.Color(0.14, 0.82, 0.48, alpha=0.18))
    c.setLineWidth(1)
    for i in range(9):
        x = WIDTH - 260 + i * 28
        c.line(x, 0, WIDTH, 260 - i * 18)

    c.setFillColor(colors.Color(0.30, 0.79, 0.94, alpha=0.10))
    c.circle(WIDTH - 130, HEIGHT - 95, 82, stroke=0, fill=1)

    c.setFillColor(colors.Color(0.19, 0.82, 0.48, alpha=0.10))
    c.circle(100, 70, 110, stroke=0, fill=1)

    c.setStrokeColor(LINE)
    c.setLineWidth(1)
    c.line(54, 56, WIDTH - 54, 56)
    c.setFillColor(MUTED)
    c.setFont("DeckRegular", 10)
    c.drawString(54, 34, "Polymarket Screener MVP")
    c.drawRightString(WIDTH - 54, 34, f"{page_num:02d} / {len(SLIDES):02d}")


def draw_slide(c: canvas.Canvas, slide: dict, page_num: int) -> None:
    draw_background(c, page_num)

    left = 72
    top = HEIGHT - 86

    c.setFillColor(GREEN)
    c.roundRect(left, top - 24, 168, 28, 14, stroke=0, fill=1)
    c.setFillColor(BG)
    c.setFont("DeckBold", 10)
    c.drawCentredString(left + 84, top - 15, slide["eyebrow"])

    c.setFillColor(TEXT)
    c.setFont("DeckBold", 38)
    title_y = top - 78
    title_y = text_lines(c, slide["title"], left, title_y, 560, "DeckBold", 38, 46, TEXT)

    subtitle_y = title_y - 12
    text_lines(c, slide["subtitle"], left, subtitle_y, 600, "DeckRegular", 17, 25, MUTED)

    bullet_y = 270
    for bullet in slide["bullets"]:
        c.setFillColor(GREEN)
        c.circle(left + 5, bullet_y + 6, 4, stroke=0, fill=1)
        bullet_y = text_lines(c, bullet, left + 20, bullet_y, 560, "DeckRegular", 16, 24, TEXT) - 6

    panel_x = WIDTH - 390
    panel_y = 145
    c.setFillColor(PANEL)
    c.roundRect(panel_x, panel_y, 304, 322, 28, stroke=0, fill=1)
    c.setStrokeColor(LINE)
    c.setLineWidth(1.5)
    c.roundRect(panel_x, panel_y, 304, 322, 28, stroke=1, fill=0)

    c.setFillColor(PANEL_2)
    c.roundRect(panel_x + 28, panel_y + 198, 248, 84, 18, stroke=0, fill=1)
    c.setFillColor(GREEN)
    c.setFont("DeckBold", 46)
    c.drawCentredString(panel_x + 152, panel_y + 224, slide["metric"])
    c.setFillColor(MUTED)
    c.setFont("DeckRegular", 14)
    c.drawCentredString(panel_x + 152, panel_y + 204, slide["metric_label"])

    c.setStrokeColor(CYAN)
    c.setLineWidth(3)
    x0 = panel_x + 54
    y0 = panel_y + 112
    points = [(x0, y0), (x0 + 44, y0 + 36), (x0 + 92, y0 + 18), (x0 + 138, y0 + 68), (x0 + 196, y0 + 96)]
    for a, b in zip(points, points[1:]):
        c.line(a[0], a[1], b[0], b[1])
    c.setFillColor(CYAN)
    for x, y in points:
        c.circle(x, y, 5, stroke=0, fill=1)

    c.setFillColor(MUTED)
    c.setFont("DeckRegular", 11)
    c.drawCentredString(panel_x + 152, panel_y + 64, "market discovery → price check → Telegram signal")


def build() -> None:
    register_fonts()
    c = canvas.Canvas(str(OUT), pagesize=(WIDTH, HEIGHT))
    c.setTitle("Polymarket Screener MVP")
    c.setAuthor("Pumpfun")

    for index, slide in enumerate(SLIDES, start=1):
        draw_slide(c, slide, index)
        c.showPage()

    c.setFillColor(BG)
    c.rect(0, 0, WIDTH, HEIGHT, stroke=0, fill=1)
    c.setFillColor(TEXT)
    c.setFont("DeckBold", 30)
    c.drawString(72, HEIGHT - 120, "Disclaimer")
    y = HEIGHT - 172
    disclaimer = (
        "Это аналитический и исследовательский инструмент. Сигналы не являются финансовой рекомендацией, "
        "не гарантируют прибыль и не означают автоматическую исполнимость сделки. MVP не принимает средства "
        "пользователей и не исполняет сделки автоматически."
    )
    text_lines(c, disclaimer, 72, y, WIDTH - 144, "DeckRegular", 18, 28, MUTED)
    c.setFillColor(GREEN)
    c.setFont("DeckBold", 16)
    c.drawString(72, 90, "Next: validate signal quality, then build operator dashboard.")
    c.showPage()

    c.save()


if __name__ == "__main__":
    build()
