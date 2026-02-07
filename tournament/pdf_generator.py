"""
============================================
ГЕНЕРАЦИЯ PDF ДЛЯ ТУРНИРОВ
============================================

Функционал:
- Генерация турнирной сетки в PDF
- Таблица результатов турнира
- Список участников
- Расписание матчей
- Красивое оформление с логотипом
"""

from reportlab.lib.pagesizes import A4, letter, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, Image, Frame, FrameBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Line, Rect
from io import BytesIO
from datetime import datetime
from django.conf import settings
import os


class TournamentPDFGenerator:
    """Генератор PDF документов для турниров"""

    def __init__(self, tournament):
        self.tournament = tournament
        self.buffer = BytesIO()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Настройка пользовательских стилей"""

        # Заголовок турнира
        self.styles.add(ParagraphStyle(
            name='TournamentTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#38b000'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        # Подзаголовок
        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#666666'),
            spaceAfter=20,
            alignment=TA_CENTER
        ))

        # Заголовок секции
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#38b000'),
            spaceAfter=15,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        ))

    def generate_bracket_pdf(self):
        """Генерация PDF с турнирной сеткой"""

        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=landscape(A4) if self.tournament.format_type == 'elimination' else A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        story = []

        # Заголовок
        story.append(Paragraph(
            f'Турнир: {self.tournament.name}',
            self.styles['TournamentTitle']
        ))

        # Информация о турнире
        info_text = f"""
        <b>Формат:</b> {self.tournament.get_format_type_display()}<br/>
        <b>Даты:</b> {self.tournament.start_date.strftime('%d.%m.%Y')} -
                      {self.tournament.end_date.strftime('%d.%m.%Y')}<br/>
        <b>Призовой фонд:</b> {self.tournament.prize_pool} ₽<br/>
        <b>Участников:</b> {self.tournament.participants.count()}
        """

        story.append(Paragraph(info_text, self.styles['Subtitle']))
        story.append(Spacer(1, 30))

        # Генерируем сетку в зависимости от формата
        if self.tournament.format_type == 'elimination':
            story.extend(self._generate_elimination_bracket())
        elif self.tournament.format_type in ['americano', 'mexicano']:
            story.extend(self._generate_americano_table())
        elif self.tournament.format_type == 'round_robin':
            story.extend(self._generate_round_robin_table())
        else:
            story.extend(self._generate_generic_matches())

        # Генерируем PDF
        doc.build(story, onFirstPage=self._add_header, onLaterPages=self._add_header)
        self.buffer.seek(0)
        return self.buffer

    def _generate_elimination_bracket(self):
        """Генерация плей-офф сетки"""
        story = []

        story.append(Paragraph('Турнирная сетка', self.styles['SectionHeader']))

        matches = self.tournament.matches.all().order_by('round_number', 'match_number')

        # Группируем матчи по раундам
        rounds = {}
        for match in matches:
            round_num = match.round_number
            if round_num not in rounds:
                rounds[round_num] = []
            rounds[round_num].append(match)

        # Генерируем таблицу для каждого раунда
        for round_num in sorted(rounds.keys()):
            round_matches = rounds[round_num]

            # Название раунда
            round_names = {
                1: 'Финал',
                2: 'Полуфинал',
                3: '1/4 финала',
                4: '1/8 финала',
            }
            round_name = round_names.get(len(rounds) - round_num + 1, f'Раунд {round_num}')

            story.append(Paragraph(round_name, self.styles['Heading3']))

            # Данные для таблицы
            data = [['Матч', 'Участник 1', 'Счет', 'Участник 2', 'Победитель']]

            for match in round_matches:
                team1 = match.team1.get_display_name() if match.team1 else 'TBD'
                team2 = match.team2.get_display_name() if match.team2 else 'TBD'
                score = f"{match.team1_score} : {match.team2_score}" if match.status == 'completed' else '-'
                winner = match.winner.get_display_name() if match.winner else '-'

                data.append([
                    f'#{match.match_number}',
                    team1,
                    score,
                    team2,
                    winner
                ])

            # Создаем таблицу
            table = Table(data, colWidths=[1.5*cm, 6*cm, 2*cm, 6*cm, 6*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#9ef01a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1a1a1a')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
            ]))

            story.append(table)
            story.append(Spacer(1, 20))

        return story

    def _generate_americano_table(self):
        """Генерация таблицы результатов Americano/Mexicano"""
        story = []

        story.append(Paragraph('Таблица результатов', self.styles['SectionHeader']))

        # Получаем участников с результатами
        participants = self.tournament.participants.all().order_by('-total_points', '-wins')

        data = [['Место', 'Участник', 'Рейтинг', 'Побед', 'Поражений', 'Очков']]

        for idx, participant in enumerate(participants, 1):
            data.append([
                str(idx),
                participant.user.get_full_name(),
                f"{participant.user.rating.current_rating:.2f}" if hasattr(participant.user, 'rating') else '-',
                str(participant.wins),
                str(participant.losses),
                str(participant.total_points)
            ])

        table = Table(data, colWidths=[2*cm, 7*cm, 3*cm, 2.5*cm, 3*cm, 2.5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#9ef01a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1a1a1a')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
            # Выделяем топ-3
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#FFD700')),  # Золото
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#C0C0C0')),  # Серебро
            ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#CD7F32')),  # Бронза
        ]))

        story.append(table)
        return story

    def _generate_round_robin_table(self):
        """Генерация таблицы кругового турнира"""
        story = []

        story.append(Paragraph('Турнирная таблица', self.styles['SectionHeader']))

        # Аналогично Americano
        return self._generate_americano_table()

    def _generate_generic_matches(self):
        """Генерация общего списка матчей"""
        story = []

        story.append(Paragraph('Расписание матчей', self.styles['SectionHeader']))

        matches = self.tournament.matches.all().order_by('scheduled_time', 'match_number')

        data = [['№', 'Дата/Время', 'Команда 1', 'Команда 2', 'Корт', 'Статус']]

        for match in matches:
            date_time = match.scheduled_time.strftime('%d.%m %H:%M') if match.scheduled_time else '-'
            team1 = match.team1.get_display_name() if match.team1 else 'TBD'
            team2 = match.team2.get_display_name() if match.team2 else 'TBD'
            court = match.court.name if match.court else '-'
            status = match.get_status_display()

            data.append([
                f'#{match.match_number}',
                date_time,
                team1,
                team2,
                court,
                status
            ])

        table = Table(data, colWidths=[1.5*cm, 3.5*cm, 6*cm, 6*cm, 3*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#9ef01a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1a1a1a')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ]))

        story.append(table)
        return story

    def _add_header(self, canvas, doc):
        """Добавление заголовка на каждую страницу"""
        canvas.saveState()

        # Логотип (если есть)
        # logo_path = os.path.join(settings.STATIC_ROOT, 'images/logo.png')
        # if os.path.exists(logo_path):
        #     canvas.drawImage(logo_path, 2*cm, doc.height + 2.5*cm, width=2*cm, height=2*cm)

        # Линия разделителя
        canvas.setStrokeColor(colors.HexColor('#9ef01a'))
        canvas.setLineWidth(2)
        canvas.line(2*cm, doc.height + 2*cm, doc.width + 2*cm, doc.height + 2*cm)

        # Футер с датой генерации
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(
            2*cm,
            1*cm,
            f'Сгенерировано: {datetime.now().strftime("%d.%m.%Y %H:%M")}'
        )

        # Номер страницы
        canvas.drawRightString(
            doc.width + 2*cm,
            1*cm,
            f'Страница {canvas.getPageNumber()}'
        )

        canvas.restoreState()

    def save_to_file(self, filepath):
        """Сохранение PDF в файл"""
        self.generate_bracket_pdf()
        with open(filepath, 'wb') as f:
            f.write(self.buffer.getvalue())


# ============================================
# ФУНКЦИИ ДЛЯ ИСПОЛЬЗОВАНИЯ В VIEWS
# ============================================

def generate_tournament_bracket_pdf(tournament):
    """
    Генерация PDF с турнирной сеткой

    Args:
        tournament: Объект Tournament

    Returns:
        BytesIO buffer с PDF или None при ошибке
    """
    try:
        generator = TournamentPDFGenerator(tournament)
        return generator.generate_bracket_pdf()
    except Exception as e:
        print(f"Ошибка генерации PDF: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_tournament_results_pdf(tournament):
    """Генерация PDF с результатами турнира"""
    return generate_tournament_bracket_pdf(tournament)


# ============================================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ В VIEWS
# ============================================

"""
# В tournament/views.py:

from django.http import HttpResponse
from tournament.pdf_generator import generate_tournament_bracket_pdf

def download_bracket_pdf(request, tournament_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)

    # Генерируем PDF
    pdf_buffer = generate_tournament_bracket_pdf(tournament)

    if pdf_buffer is None:
        return HttpResponse('Ошибка генерации PDF', status=500)

    # Возвращаем как файл для скачивания
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="tournament_{tournament.id}_bracket.pdf"'

    return response
"""
