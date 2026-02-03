"""
Генераторы турнирных сеток для ПАДДЛ турниров
Поддерживает: Americano, Mexicano, Team форматы, Doubles Bracket
"""
import math
import random
from typing import List, Tuple
from django.contrib.auth.models import User


class AmericanoGenerator:
    """
    Генератор для формата Americano

    Принцип:
    - Каждый игрок соревнуется индивидуально
    - Но играет в ПАРАХ (2v2)
    - Партнеры МЕНЯЮТСЯ каждый раунд
    - Цель: каждый играет с каждым И против каждого
    - Очки начисляются индивидуально

    Алгоритм: Modified Round Robin с ротацией партнеров
    """

    @staticmethod
    def generate(tournament):
        """
        Генерация всех раундов Americano

        Возвращает: список созданных матчей
        """
        from .models import TournamentParticipant, PadelTeam, TournamentMatch, TournamentRound

        # Получаем участников
        participants = list(
            tournament.participants.filter(payment_status='paid')
            .order_by('seed', 'registered_at')
        )

        num_players = len(participants)

        # Валидация
        if num_players < 4:
            raise ValueError("Минимум 4 участника для Americano")

        # Предупреждение если не кратно 4
        if num_players % 4 != 0:
            print(f"⚠️ Количество игроков ({num_players}) не кратно 4. "
                  f"Некоторые будут иметь bye раунды")

        # Очищаем старые данные
        tournament.matches.all().delete()
        tournament.teams.filter(is_temporary=True).delete()
        tournament.rounds.all().delete()

        # Сброс статистики участников
        for p in participants:
            p.total_points = 0
            p.matches_played = 0
            p.matches_won = 0
            p.matches_lost = 0
            p.current_rank = None
            p.save()

        players = [p.user for p in participants]

        # Количество раундов
        # Для Americano: (n-1) раундов или больше, чтобы каждый сыграл со всеми
        num_rounds = AmericanoGenerator._calculate_rounds(num_players)

        print(f"🎾 Генерация Americano: {num_players} игроков, {num_rounds} раундов")

        all_matches = []

        for round_num in range(1, num_rounds + 1):
            # Создаем раунд
            round_obj = TournamentRound.objects.create(
                tournament=tournament,
                round_number=round_num,
                name=f'Раунд {round_num}'
            )

            # Генерируем пары для этого раунда
            pairings = AmericanoGenerator._generate_round_pairings(
                players,
                round_num,
                num_players
            )

            # Создаем матчи из пар
            match_num = 1

            for team1_players, team2_players in pairings:
                # Создаем временные команды
                team1 = PadelTeam.objects.create(
                    tournament=tournament,
                    player1=team1_players[0],
                    player2=team1_players[1],
                    is_temporary=True,
                    round_number=round_num
                )

                team2 = PadelTeam.objects.create(
                    tournament=tournament,
                    player1=team2_players[0],
                    player2=team2_players[1],
                    is_temporary=True,
                    round_number=round_num
                )

                # Создаем матч
                match = TournamentMatch.objects.create(
                    tournament=tournament,
                    round=round_num,
                    match_number=match_num,
                    team1=team1,
                    team2=team2,
                    status='scheduled'
                )

                all_matches.append(match)
                match_num += 1

            print(f"  Раунд {round_num}: {len(pairings)} матчей")

            # Ротация игроков для следующего раунда
            players = AmericanoGenerator._rotate_players(players)

        print(f"✅ Создано {len(all_matches)} матчей")
        return all_matches

    @staticmethod
    def _calculate_rounds(num_players):
        """Рассчитать количество раундов"""
        # Для корректного Americano нужно достаточно раундов,
        # чтобы каждый сыграл с каждым и против каждого
        # Формула: примерно (n-1) до 2*(n-1) раундов

        if num_players <= 4:
            return 3  # Минимум 3 раунда для 4 игроков

        # Стандартно: n-1 раунд
        return num_players - 1

    @staticmethod
    def _generate_round_pairings(players, round_num, total_players):
        """
        Генерация пар для одного раунда

        Используем алгоритм круговой системы с модификацией для пар

        Возвращает: список кортежей ((p1, p2), (p3, p4)) - матчи
        """
        n = len(players)
        pairings = []

        # Разбиваем игроков на пары
        # Используем круговой алгоритм
        half = n // 2

        for i in range(half):
            # Первая пара
            team1_player1 = players[i]
            team1_player2 = players[n - 1 - i]

            # Вторая пара (следующие два игрока)
            if i + half < n - i - 1:
                team2_player1 = players[i + half] if i + half < n else None
                team2_player2 = players[n - 1 - i - half] if n - 1 - i - half >= 0 else None

                if team2_player1 and team2_player2:
                    pairings.append((
                        (team1_player1, team1_player2),
                        (team2_player1, team2_player2)
                    ))
                elif team1_player1 and team1_player2:
                    # Если нечетное количество, одна пара может не иметь соперника
                    pass

        # Альтернативный подход: разбить на четверки
        pairings_v2 = []
        for i in range(0, n, 4):
            if i + 3 < n:
                # Берем 4 игроков
                p1, p2, p3, p4 = players[i], players[i+1], players[i+2], players[i+3]

                # Формируем матч: (p1+p2) vs (p3+p4)
                pairings_v2.append(((p1, p2), (p3, p4)))

        return pairings_v2 if pairings_v2 else pairings

    @staticmethod
    def _rotate_players(players):
        """
        Ротация игроков для следующего раунда

        Алгоритм круговой системы:
        - Первый игрок остается на месте
        - Остальные ротируются по часовой стрелке
        """
        if len(players) <= 1:
            return players

        # Первый остается, последний становится вторым, остальные сдвигаются
        return [players[0]] + [players[-1]] + players[1:-1]


class MexicanoGenerator:
    """
    Генератор для формата Mexicano

    Принцип:
    - Как Americano, но пары формируются по РЕЙТИНГУ
    - После каждого раунда игроки ранжируются по очкам
    - Следующие пары: 1+2 vs 3+4, 5+6 vs 7+8 и т.д.
    - Матчи становятся более сбалансированными со временем
    """

    @staticmethod
    def generate_first_round(tournament):
        """
        Генерация первого раунда Mexicano

        Первый раунд - случайные пары (или по посеву)
        """
        from .models import TournamentParticipant, PadelTeam, TournamentMatch, TournamentRound

        participants = list(
            tournament.participants.filter(payment_status='paid')
            .order_by('seed', 'registered_at')
        )

        num_players = len(participants)

        if num_players < 4:
            raise ValueError("Минимум 4 участника для Mexicano")

        # Очищаем старые данные
        tournament.matches.all().delete()
        tournament.teams.filter(is_temporary=True).delete()
        tournament.rounds.all().delete()

        # Сброс статистики
        for p in participants:
            p.total_points = 0
            p.matches_played = 0
            p.matches_won = 0
            p.matches_lost = 0
            p.current_rank = None
            p.save()

        # Создаем первый раунд
        round_obj = TournamentRound.objects.create(
            tournament=tournament,
            round_number=1,
            name='Раунд 1'
        )

        # Случайное перемешивание для первого раунда
        players = [p.user for p in participants]
        random.shuffle(players)

        matches = []
        match_num = 1

        # Формируем матчи по 4 игрока
        for i in range(0, num_players, 4):
            if i + 3 < num_players:
                team1 = PadelTeam.objects.create(
                    tournament=tournament,
                    player1=players[i],
                    player2=players[i+1],
                    is_temporary=True,
                    round_number=1
                )

                team2 = PadelTeam.objects.create(
                    tournament=tournament,
                    player1=players[i+2],
                    player2=players[i+3],
                    is_temporary=True,
                    round_number=1
                )

                match = TournamentMatch.objects.create(
                    tournament=tournament,
                    round=1,
                    match_number=match_num,
                    team1=team1,
                    team2=team2,
                    status='scheduled'
                )

                matches.append(match)
                match_num += 1

        print(f"🎾 Mexicano Раунд 1: {len(matches)} матчей (случайные пары)")
        return matches

    @staticmethod
    def generate_next_round(tournament):
        """
        Генерация следующего раунда Mexicano

        Пары формируются по текущему рейтингу:
        - Топ-2 играют вместе против 3-4
        - 5-6 против 7-8 и т.д.
        """
        from .models import TournamentParticipant, PadelTeam, TournamentMatch, TournamentRound

        # Получаем текущее количество раундов
        current_round_num = tournament.rounds.count()
        next_round_num = current_round_num + 1

        # Получаем участников, отсортированных по очкам
        participants = list(
            tournament.participants.filter(payment_status='paid')
            .order_by('-total_points', '-matches_won', 'registered_at')
        )

        num_players = len(participants)

        # Создаем раунд
        round_obj = TournamentRound.objects.create(
            tournament=tournament,
            round_number=next_round_num,
            name=f'Раунд {next_round_num}'
        )

        # Обновляем ранги
        for rank, participant in enumerate(participants, start=1):
            participant.current_rank = rank
            participant.save()

        print(f"🎾 Mexicano Раунд {next_round_num}:")
        print(f"  Топ-3: {participants[0].user.get_full_name()} ({participants[0].total_points} pts), "
              f"{participants[1].user.get_full_name()} ({participants[1].total_points} pts), "
              f"{participants[2].user.get_full_name() if len(participants) > 2 else 'N/A'}")

        matches = []
        match_num = 1

        # Формируем пары по рейтингу: 1+2 vs 3+4, 5+6 vs 7+8
        for i in range(0, num_players, 4):
            if i + 3 < num_players:
                # Берем 4 игрока подряд по рейтингу
                p1, p2, p3, p4 = participants[i:i+4]

                # Формируем пары: 1+2 vs 3+4
                team1 = PadelTeam.objects.create(
                    tournament=tournament,
                    player1=p1.user,
                    player2=p2.user,
                    is_temporary=True,
                    round_number=next_round_num
                )

                team2 = PadelTeam.objects.create(
                    tournament=tournament,
                    player1=p3.user,
                    player2=p4.user,
                    is_temporary=True,
                    round_number=next_round_num
                )

                match = TournamentMatch.objects.create(
                    tournament=tournament,
                    round=next_round_num,
                    match_number=match_num,
                    team1=team1,
                    team2=team2,
                    status='scheduled'
                )

                matches.append(match)
                print(f"  Матч {match_num}: ({p1.user.get_full_name()}+{p2.user.get_full_name()}) vs "
                      f"({p3.user.get_full_name()}+{p4.user.get_full_name()})")
                match_num += 1

        print(f"✅ Создано {len(matches)} матчей")
        return matches


class DoublesEliminationGenerator:
    """
    Генератор для Doubles Elimination (олимпийская система для пар)

    Принцип:
    - Постоянные пары
    - Олимпийская система (single elimination)
    - Пары выбывают после одного поражения
    """

    @staticmethod
    def generate(tournament):
        """
        Генерация сетки Doubles Elimination

        Аналогично существующему SingleElimination, но для пар
        """
        from .models import TournamentParticipant, PadelTeam, TournamentMatch, TournamentRound

        # Получаем участников
        participants = list(
            tournament.participants.filter(payment_status='paid')
            .order_by('seed', 'registered_at')
        )

        if len(participants) < 2:
            raise ValueError("Минимум 2 пары для Doubles Elimination")

        # Очищаем старые данные
        tournament.matches.all().delete()
        tournament.teams.filter(is_temporary=False).delete()
        tournament.rounds.all().delete()

        # Создаем постоянные команды
        teams = []
        for participant in participants:
            if not participant.partner:
                raise ValueError(f"Участник {participant.user.get_full_name()} не указал партнера")

            team = PadelTeam.objects.create(
                tournament=tournament,
                player1=participant.user,
                player2=participant.partner,
                name=participant.team_name or '',
                seed=participant.seed,
                is_temporary=False
            )
            teams.append(team)

        num_teams = len(teams)
        num_rounds = math.ceil(math.log2(num_teams))
        bracket_size = 2 ** num_rounds

        print(f"🎾 Doubles Elimination: {num_teams} пар, {num_rounds} раундов")

        # Создаем раунды
        round_names = DoublesEliminationGenerator._get_round_names(num_rounds)
        for i in range(num_rounds):
            TournamentRound.objects.create(
                tournament=tournament,
                round_number=i + 1,
                name=round_names[i]
            )

        # Генерируем все матчи
        all_matches = []

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

        # Связываем матчи (next_match)
        for round_num in range(1, num_rounds):
            current_round_matches = [m for m in all_matches if m.round == round_num]
            next_round_matches = [m for m in all_matches if m.round == round_num + 1]

            for i, match in enumerate(current_round_matches):
                next_match_index = i // 2
                match.next_match = next_round_matches[next_match_index]
                match.save()

        # Распределяем команды в первый раунд с посевом
        first_round_matches = [m for m in all_matches if m.round == 1]
        seeded_positions = DoublesEliminationGenerator._get_seeded_positions(bracket_size)

        for i, position in enumerate(seeded_positions[:num_teams]):
            match_index = position // 2
            team = teams[i]

            if position % 2 == 0:
                first_round_matches[match_index].team1 = team
            else:
                first_round_matches[match_index].team2 = team

            first_round_matches[match_index].save()

        # Обработка bye
        for match in first_round_matches:
            if match.team1 and not match.team2:
                match.winning_team = match.team1
                match.status = 'walkover'
                match.save()
                if match.next_match:
                    if match.match_number % 2 == 1:
                        match.next_match.team1 = match.team1
                    else:
                        match.next_match.team2 = match.team1
                    match.next_match.save()

            elif match.team2 and not match.team1:
                match.winning_team = match.team2
                match.status = 'walkover'
                match.save()
                if match.next_match:
                    if match.match_number % 2 == 1:
                        match.next_match.team1 = match.team2
                    else:
                        match.next_match.team2 = match.team2
                    match.next_match.save()

        print(f"✅ Создано {len(all_matches)} матчей")
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
        else:
            names = []
            for i in range(num_rounds - 2):
                power = num_rounds - i
                names.append(f'1/{2**power} финала')
            names.extend(['Полуфинал', 'Финал'])
            return names

    @staticmethod
    def _get_seeded_positions(bracket_size):
        """Алгоритм посева"""
        if bracket_size == 2:
            return [0, 1]

        half_size = bracket_size // 2
        half_positions = DoublesEliminationGenerator._get_seeded_positions(half_size)

        positions = []
        for pos in half_positions:
            positions.append(pos)
            positions.append(bracket_size - 1 - pos)

        return positions
