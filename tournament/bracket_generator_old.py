"""
Генератор турнирных сеток
"""
import math
from .models import Tournament, TournamentMatch, TournamentParticipant, TournamentRound


class BracketGenerator:
    """Генератор турнирных сеток"""

    @staticmethod
    def generate_single_elimination(tournament):
        """
        Генерация олимпийской системы (Single Elimination)

        Логика:
        - Участники выбываютпосле первого проигрыша
        - Количество раундов = log2(participants)
        - Все матчи генерируются заранее
        """
        # Получаем оплаченных участников с посевом
        participants = list(
            tournament.participants.filter(payment_status='paid').order_by('seed', 'registered_at')
        )

        num_participants = len(participants)
        if num_participants < 2:
            raise ValueError("Недостаточно участников для создания турнира")

        # Определяем количество раундов
        num_rounds = math.ceil(math.log2(num_participants))

        # Ближайшая степень двойки
        bracket_size = 2 ** num_rounds

        # Удаляем старые матчи если есть
        tournament.matches.all().delete()
        tournament.rounds.all().delete()

        # Создаем раунды
        round_names = BracketGenerator._get_round_names(num_rounds)
        rounds_created = []
        for i in range(num_rounds):
            round_obj = TournamentRound.objects.create(
                tournament=tournament,
                round_number=i + 1,
                name=round_names[i]
            )
            rounds_created.append(round_obj)

        # Генерируем все матчи для всех раундов
        all_matches = []

        # Создаем матчи для финального раунда и двигаемся назад
        for round_num in range(num_rounds, 0, -1):
            matches_in_round = 2 ** (round_num - 1)

            for match_num in range(matches_in_round):
                match = TournamentMatch.objects.create(
                    tournament=tournament,
                    round=round_num,
                    match_number=match_num + 1,
                    status='scheduled'
                )
                all_matches.append(match)

        # Связываем матчи (следующий раунд)
        for round_num in range(1, num_rounds):
            current_round_matches = [m for m in all_matches if m.round == round_num]
            next_round_matches = [m for m in all_matches if m.round == round_num + 1]

            for i, match in enumerate(current_round_matches):
                next_match_index = i // 2
                match.next_match = next_round_matches[next_match_index]
                match.save()

        # Распределяем участников в первый раунд
        first_round_matches = [m for m in all_matches if m.round == 1]

        # Если участников меньше чем мест в сетке, некоторые получают bye
        participants_list = [p.user for p in participants]

        # Заполняем участников по алгоритму посева
        seeded_positions = BracketGenerator._get_seeded_positions(bracket_size)

        for i, position in enumerate(seeded_positions[:num_participants]):
            match_index = position // 2
            if position % 2 == 0:
                first_round_matches[match_index].player1 = participants_list[i]
            else:
                first_round_matches[match_index].player2 = participants_list[i]

            first_round_matches[match_index].save()

        # Обрабатываем bye (когда у игрока нет соперника, он автоматически проходит дальше)
        for match in first_round_matches:
            if match.player1 and not match.player2:
                # Player1 проходит автоматически
                match.winner = match.player1
                match.status = 'walkover'
                match.save()
                if match.next_match:
                    if match.match_number % 2 == 1:
                        match.next_match.player1 = match.player1
                    else:
                        match.next_match.player2 = match.player1
                    match.next_match.save()

            elif match.player2 and not match.player1:
                # Player2 проходит автоматически
                match.winner = match.player2
                match.status = 'walkover'
                match.save()
                if match.next_match:
                    if match.match_number % 2 == 1:
                        match.next_match.player1 = match.player2
                    else:
                        match.next_match.player2 = match.player2
                    match.next_match.save()

        return all_matches

    @staticmethod
    def generate_round_robin(tournament):
        """
        Генерация круговой системы (Round Robin)

        Логика:
        - Каждый играет с каждым один раз
        - Количество матчей = n * (n-1) / 2
        - Количество раундов = n - 1 (если четное число участников)
        """
        participants = list(
            tournament.participants.filter(payment_status='paid').order_by('seed', 'registered_at')
        )

        num_participants = len(participants)
        if num_participants < 2:
            raise ValueError("Недостаточно участников")

        # Удаляем старые матчи
        tournament.matches.all().delete()
        tournament.rounds.all().delete()

        participants_list = [p.user for p in participants]

        # Если нечетное количество, добавляем "фиктивного" участника (bye)
        if num_participants % 2 == 1:
            participants_list.append(None)
            num_participants += 1

        num_rounds = num_participants - 1
        matches_per_round = num_participants // 2

        # Создаем раунды
        for round_num in range(1, num_rounds + 1):
            TournamentRound.objects.create(
                tournament=tournament,
                round_number=round_num,
                name=f'Тур {round_num}'
            )

        # Алгоритм круговой системы (Round Robin Scheduling)
        # https://en.wikipedia.org/wiki/Round-robin_tournament#Scheduling_algorithm
        all_matches = []
        match_counter = 1

        for round_num in range(1, num_rounds + 1):
            for match_in_round in range(matches_per_round):
                player1_idx = match_in_round
                player2_idx = num_participants - 1 - match_in_round

                player1 = participants_list[player1_idx]
                player2 = participants_list[player2_idx]

                # Пропускаем матчи с bye
                if player1 is None or player2 is None:
                    continue

                match = TournamentMatch.objects.create(
                    tournament=tournament,
                    round=round_num,
                    match_number=match_counter,
                    player1=player1,
                    player2=player2,
                    status='scheduled'
                )
                all_matches.append(match)
                match_counter += 1

            # Ротация участников (первый остается на месте)
            participants_list = [participants_list[0]] + [participants_list[-1]] + participants_list[1:-1]

        return all_matches

    @staticmethod
    def _get_round_names(num_rounds):
        """Получить названия раундов"""
        if num_rounds == 1:
            return ['Финал']
        elif num_rounds == 2:
            return ['Полуфинал', 'Финал']
        elif num_rounds == 3:
            return ['1/4 финала', 'Полуфинал', 'Финал']
        elif num_rounds == 4:
            return ['1/8 финала', '1/4 финала', 'Полуфинал', 'Финал']
        elif num_rounds == 5:
            return ['1/16 финала', '1/8 финала', '1/4 финала', 'Полуфинал', 'Финал']
        elif num_rounds == 6:
            return ['1/32 финала', '1/16 финала', '1/8 финала', '1/4 финала', 'Полуфинал', 'Финал']
        elif num_rounds == 7:
            return ['1/64 финала', '1/32 финала', '1/16 финала', '1/8 финала', '1/4 финала', 'Полуфинал', 'Финал']
        else:
            names = []
            for i in range(num_rounds - 2):
                power = num_rounds - i
                names.append(f'1/{2**power} финала')
            names.extend(['Полуфинал', 'Финал'])
            return names

    @staticmethod
    def _get_seeded_positions(bracket_size):
        """
        Получить позиции для посева (seeding)

        Алгоритм гарантирует, что сильнейшие игроки встретятся в финале
        Например, для 8 участников: [1, 8, 4, 5, 2, 7, 3, 6]
        """
        if bracket_size == 2:
            return [0, 1]

        # Рекурсивно строим позиции
        half_size = bracket_size // 2
        half_positions = BracketGenerator._get_seeded_positions(half_size)

        positions = []
        for pos in half_positions:
            positions.append(pos)
            positions.append(bracket_size - 1 - pos)

        return positions
