"""
Генератор Mexicano для обычных игр (не турниров)
Адаптация из tournament.bracket_generator.MexicanoGenerator

Mexicano - формат игры где пары формируются динамически по рейтингу участников.
После каждого раунда игроки ранжируются по очкам, и сильнейшие играют вместе.
"""
import random
from booking.models import Booking, GameParticipant, GameRound
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


class BookingMexicanoGenerator:
    """
    Генератор раундов Mexicano для обычных игр

    Mexicano отличается от Americano тем, что после первого раунда
    пары формируются не случайно, а по рейтингу участников:
    - Топ-2 по очкам играют вместе
    - 3-4 места играют вместе
    - И так далее
    """

    @staticmethod
    @transaction.atomic
    def generate_first_round(booking):
        """
        Генерация первого раунда Mexicano

        Для первого раунда используется случайное распределение,
        так как у участников еще нет очков.

        Args:
            booking: Объект Booking с game_mode='mexicano'

        Returns:
            List созданных GameRound объектов

        Raises:
            ValueError: Если участников меньше 4 или количество не кратно 4
        """
        # Получаем всех участников
        participants = list(booking.game_participants.filter(
            status='joined'
        ).select_related('user'))

        participant_count = len(participants)

        # Валидация
        if participant_count < 4:
            raise ValueError("Минимум 4 участника для Mexicano")

        if participant_count % 4 != 0:
            raise ValueError(f"Количество участников должно быть кратно 4. Сейчас: {participant_count}")

        # Случайное перемешивание для первого раунда
        random.shuffle(participants)

        # Создаем раунды
        matches = []
        match_number = 1

        for i in range(0, participant_count, 4):
            p1, p2, p3, p4 = participants[i:i+4]

            # Создаем раунд/матч
            game_round = GameRound.objects.create(
                booking=booking,
                round_number=1,
                match_number=match_number,
                team1_player1=p1.user,
                team1_player2=p2.user,
                team2_player1=p3.user,
                team2_player2=p4.user,
                is_completed=False
            )
            matches.append(game_round)
            logger.info(f"Mexicano Round 1, Match {match_number}: {p1.user} + {p2.user} vs {p3.user} + {p4.user}")
            match_number += 1

        # Обновляем статус игры
        booking.current_round = 1
        booking.game_status = 'in_progress'
        booking.save()

        logger.info(f"Сгенерирован 1 раунд Mexicano для игры #{booking.id}. Создано {len(matches)} матчей.")

        return matches

    @staticmethod
    @transaction.atomic
    def generate_next_round(booking):
        """
        Генерация следующего раунда Mexicano

        Пары формируются по рейтингу участников:
        - Сортируем участников по total_points
        - Топ-2 играют вместе против 3-4
        - 5-6 играют вместе против 7-8
        - И так далее

        Args:
            booking: Объект Booking с game_mode='mexicano'

        Returns:
            List созданных GameRound объектов

        Raises:
            ValueError: Если недостаточно участников
        """
        # Получаем участников, отсортированных по очкам (убывание)
        participants = list(
            booking.game_participants.filter(status='joined')
            .order_by('-total_points', 'user__username')  # При равенстве очков - по имени
        )

        participant_count = len(participants)

        if participant_count < 4:
            raise ValueError("Недостаточно участников для следующего раунда")

        if participant_count % 4 != 0:
            raise ValueError(f"Количество участников должно быть кратно 4. Сейчас: {participant_count}")

        next_round_number = booking.current_round + 1

        # Создаем матчи по рейтингу
        matches = []
        match_number = 1

        for i in range(0, participant_count, 4):
            # Топ-2 из блока по 4 человека играют вместе
            p1, p2, p3, p4 = participants[i:i+4]

            game_round = GameRound.objects.create(
                booking=booking,
                round_number=next_round_number,
                match_number=match_number,
                team1_player1=p1.user,  # 1 место
                team1_player2=p2.user,  # 2 место
                team2_player1=p3.user,  # 3 место
                team2_player2=p4.user,  # 4 место
                is_completed=False
            )
            matches.append(game_round)

            logger.info(
                f"Mexicano Round {next_round_number}, Match {match_number}: "
                f"{p1.user} ({p1.total_points}pts) + {p2.user} ({p2.total_points}pts) vs "
                f"{p3.user} ({p3.total_points}pts) + {p4.user} ({p4.total_points}pts)"
            )
            match_number += 1

        # Обновляем текущий раунд
        booking.current_round = next_round_number
        booking.save()

        logger.info(
            f"Сгенерирован раунд {next_round_number} Mexicano для игры #{booking.id}. "
            f"Создано {len(matches)} матчей."
        )

        return matches

    @staticmethod
    def can_generate_next_round(booking):
        """
        Проверяет, можно ли генерировать следующий раунд

        Условия:
        - Все раунды текущего раунда завершены
        - Не превышен лимит раундов

        Args:
            booking: Объект Booking

        Returns:
            tuple: (can_generate: bool, reason: str)
        """
        current_round_number = booking.current_round

        # Проверяем, завершены ли все матчи текущего раунда
        uncompleted_rounds = booking.game_rounds.filter(
            round_number=current_round_number,
            is_completed=False
        ).count()

        if uncompleted_rounds > 0:
            return False, f"Не все матчи раунда {current_round_number} завершены ({uncompleted_rounds} осталось)"

        # Проверяем лимит раундов
        if current_round_number >= booking.rounds_count:
            return False, f"Достигнут лимит раундов ({booking.rounds_count})"

        return True, "OK"
