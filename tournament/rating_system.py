"""
============================================
СИСТЕМА РЕЙТИНГОВ ДЛЯ ТУРНИРОВ
============================================

Функционал:
- Расчет рейтингов по системе Elo
- Обновление рейтингов после матчей
- Обновление рейтингов после турниров
- Учет силы соперников
- История изменений рейтингов
"""

from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
import math
import logging

logger = logging.getLogger(__name__)


class EloRatingSystem:
    """
    Реализация системы рейтингов Elo для падел-тенниса

    K-фактор определяет скорость изменения рейтинга:
    - Новые игроки (< 30 игр): K = 40
    - Обычные игроки: K = 20
    - Профи (рейтинг > 2400): K = 10
    """

    # K-факторы для разных категорий игроков
    K_FACTOR_NEW = 40      # Новые игроки (< 30 игр)
    K_FACTOR_NORMAL = 20   # Обычные игроки
    K_FACTOR_PRO = 10      # Профессионалы (рейтинг > 2400)

    # Начальный рейтинг
    INITIAL_RATING = 1500

    # Множитель для турниров (турнирные игры важнее обычных)
    TOURNAMENT_MULTIPLIER = 1.5

    @staticmethod
    def get_k_factor(player_rating, games_played):
        """
        Получить K-фактор для игрока

        Args:
            player_rating: текущий рейтинг игрока
            games_played: количество сыгранных игр

        Returns:
            int: K-фактор
        """
        if games_played < 30:
            return EloRatingSystem.K_FACTOR_NEW
        elif player_rating > 2400:
            return EloRatingSystem.K_FACTOR_PRO
        else:
            return EloRatingSystem.K_FACTOR_NORMAL

    @staticmethod
    def calculate_expected_score(rating_a, rating_b):
        """
        Рассчитать ожидаемый результат для игрока A против игрока B

        Args:
            rating_a: рейтинг игрока A
            rating_b: рейтинг игрока B

        Returns:
            float: ожидаемый результат (0-1)
        """
        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

    @staticmethod
    def calculate_new_rating(current_rating, expected_score, actual_score, k_factor=20):
        """
        Рассчитать новый рейтинг после матча

        Args:
            current_rating: текущий рейтинг
            expected_score: ожидаемый результат
            actual_score: фактический результат (1 = победа, 0 = поражение, 0.5 = ничья)
            k_factor: K-фактор

        Returns:
            float: новый рейтинг
        """
        return current_rating + k_factor * (actual_score - expected_score)

    @staticmethod
    def update_match_ratings(winner_rating, loser_rating, winner_games, loser_games, is_tournament=False):
        """
        Обновить рейтинги двух игроков после матча

        Args:
            winner_rating: объект PlayerRating победителя
            loser_rating: объект PlayerRating проигравшего
            winner_games: количество игр победителя
            loser_games: количество игр проигравшего
            is_tournament: турнирный матч или нет

        Returns:
            tuple: (новый рейтинг победителя, новый рейтинг проигравшего, изменение)
        """
        # Текущие рейтинги
        winner_current = winner_rating.current_rating
        loser_current = loser_rating.current_rating

        # Получаем K-факторы
        winner_k = EloRatingSystem.get_k_factor(winner_current, winner_games)
        loser_k = EloRatingSystem.get_k_factor(loser_current, loser_games)

        # Множитель для турнира
        multiplier = EloRatingSystem.TOURNAMENT_MULTIPLIER if is_tournament else 1.0

        # Рассчитываем ожидаемые результаты
        winner_expected = EloRatingSystem.calculate_expected_score(winner_current, loser_current)
        loser_expected = EloRatingSystem.calculate_expected_score(loser_current, winner_current)

        # Рассчитываем новые рейтинги
        winner_new = EloRatingSystem.calculate_new_rating(
            winner_current,
            winner_expected,
            1.0,  # Победа
            winner_k * multiplier
        )

        loser_new = EloRatingSystem.calculate_new_rating(
            loser_current,
            loser_expected,
            0.0,  # Поражение
            loser_k * multiplier
        )

        rating_change = winner_new - winner_current

        return winner_new, loser_new, rating_change


class TournamentRatingUpdater:
    """Обновление рейтингов после турнира"""

    @staticmethod
    @transaction.atomic
    def update_ratings_after_tournament(tournament):
        """
        Обновить рейтинги всех участников турнира

        Args:
            tournament: объект Tournament

        Returns:
            tuple: (success: bool, message: str, updates: dict)
        """
        if tournament.status != 'completed':
            return False, "Турнир не завершен", {}

        try:
            from .models import TournamentMatch, TournamentParticipant
            from users.models import PlayerRating

            updates = {}
            updated_count = 0

            # Получаем все завершенные матчи турнира
            matches = TournamentMatch.objects.filter(
                tournament=tournament,
                status='completed',
                winner__isnull=False
            ).select_related(
                'team1__player1',
                'team1__player2',
                'team2__player1',
                'team2__player2',
                'winner__player1',
                'winner__player2'
            )

            logger.info(f"Обновление рейтингов для турнира {tournament.name}: {matches.count()} матчей")

            # Обрабатываем каждый матч
            for match in matches:
                # Определяем победителей и проигравших
                if match.winner == match.team1:
                    winner_team = match.team1
                    loser_team = match.team2
                else:
                    winner_team = match.team2
                    loser_team = match.team1

                # Обновляем рейтинги для игроков команд
                winner_players = [winner_team.player1, winner_team.player2] if winner_team.player2 else [winner_team.player1]
                loser_players = [loser_team.player1, loser_team.player2] if loser_team.player2 else [loser_team.player1]

                # Обновляем рейтинг каждого игрока
                for winner in winner_players:
                    for loser in loser_players:
                        winner_rating, _ = PlayerRating.objects.get_or_create(
                            user=winner,
                            defaults={'current_rating': EloRatingSystem.INITIAL_RATING}
                        )
                        loser_rating, _ = PlayerRating.objects.get_or_create(
                            user=loser,
                            defaults={'current_rating': EloRatingSystem.INITIAL_RATING}
                        )

                        # Получаем количество игр
                        winner_participant = TournamentParticipant.objects.filter(
                            tournament=tournament,
                            user=winner
                        ).first()
                        loser_participant = TournamentParticipant.objects.filter(
                            tournament=tournament,
                            user=loser
                        ).first()

                        winner_games = winner_participant.wins + winner_participant.losses if winner_participant else 0
                        loser_games = loser_participant.wins + loser_participant.losses if loser_participant else 0

                        # Рассчитываем новые рейтинги
                        winner_new, loser_new, rating_change = EloRatingSystem.update_match_ratings(
                            winner_rating,
                            loser_rating,
                            winner_games,
                            loser_games,
                            is_tournament=True
                        )

                        # Обновляем рейтинги
                        old_winner_rating = winner_rating.current_rating
                        old_loser_rating = loser_rating.current_rating

                        winner_rating.current_rating = winner_new
                        winner_rating.save()

                        loser_rating.current_rating = loser_new
                        loser_rating.save()

                        # Сохраняем информацию об обновлениях
                        updates[winner.username] = {
                            'old': old_winner_rating,
                            'new': winner_new,
                            'change': winner_new - old_winner_rating
                        }
                        updates[loser.username] = {
                            'old': old_loser_rating,
                            'new': loser_new,
                            'change': loser_new - old_loser_rating
                        }

                        updated_count += 1

                        logger.info(
                            f"Матч #{match.id}: {winner.username} "
                            f"({old_winner_rating:.1f} → {winner_new:.1f}, "
                            f"+{winner_new - old_winner_rating:.1f}) победил "
                            f"{loser.username} ({old_loser_rating:.1f} → {loser_new:.1f}, "
                            f"{loser_new - old_loser_rating:.1f})"
                        )

            # Дополнительно: бонусы за места в турнире
            TournamentRatingUpdater._apply_placement_bonuses(tournament, updates)

            message = f"Успешно обновлено {updated_count} пар игроков в {matches.count()} матчах"
            logger.info(f"Турнир {tournament.name}: {message}")

            return True, message, updates

        except Exception as e:
            logger.error(f"Ошибка обновления рейтингов турнира {tournament.id}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, f"Ошибка: {str(e)}", {}

    @staticmethod
    def _apply_placement_bonuses(tournament, updates):
        """
        Применить бонусы за места в турнире

        Топ-3 получают дополнительные очки:
        - 1 место: +50 очков
        - 2 место: +30 очков
        - 3 место: +15 очков
        """
        from .models import TournamentParticipant
        from users.models import PlayerRating

        PLACEMENT_BONUSES = {
            1: 50,
            2: 30,
            3: 15
        }

        # Получаем финальные позиции участников
        participants = TournamentParticipant.objects.filter(
            tournament=tournament,
            final_position__isnull=False
        ).select_related('user')

        for participant in participants:
            if participant.final_position in PLACEMENT_BONUSES:
                bonus = PLACEMENT_BONUSES[participant.final_position]

                try:
                    rating = PlayerRating.objects.get(user=participant.user)
                    old_rating = rating.current_rating
                    rating.current_rating += bonus
                    rating.save()

                    # Обновляем информацию об изменениях
                    if participant.user.username in updates:
                        updates[participant.user.username]['new'] += bonus
                        updates[participant.user.username]['change'] += bonus
                    else:
                        updates[participant.user.username] = {
                            'old': old_rating,
                            'new': old_rating + bonus,
                            'change': bonus
                        }

                    logger.info(
                        f"Бонус за {participant.final_position} место: "
                        f"{participant.user.username} +{bonus} очков"
                    )

                except PlayerRating.DoesNotExist:
                    logger.warning(f"PlayerRating не найден для {participant.user.username}")


# ============================================
# ФУНКЦИЯ ДЛЯ ИСПОЛЬЗОВАНИЯ В utils.py
# ============================================

def update_player_ratings_after_tournament(tournament):
    """
    Обновление рейтингов игроков после завершения турнира

    Args:
        tournament: объект Tournament

    Returns:
        tuple: (success: bool, message: str)
    """
    success, message, updates = TournamentRatingUpdater.update_ratings_after_tournament(tournament)

    # Выводим сводку изменений
    if success and updates:
        print("\n" + "="*50)
        print(f"ОБНОВЛЕНИЕ РЕЙТИНГОВ: {tournament.name}")
        print("="*50)
        for username, data in sorted(updates.items(), key=lambda x: x[1]['change'], reverse=True):
            change_str = f"+{data['change']:.1f}" if data['change'] >= 0 else f"{data['change']:.1f}"
            print(f"{username:20s}: {data['old']:7.1f} → {data['new']:7.1f} ({change_str})")
        print("="*50 + "\n")

    return success, message


# ============================================
# ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ
# ============================================

"""
# В tournament/views.py:

from tournament.rating_system import update_player_ratings_after_tournament

@login_required
def complete_tournament(request, tournament_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)

    # ... завершение турнира ...

    # Обновляем рейтинги
    success, message = update_player_ratings_after_tournament(tournament)

    if success:
        messages.success(request, f'Турнир завершен! {message}')
    else:
        messages.warning(request, f'Турнир завершен, но {message}')

    return redirect('tournament_detail', tournament_id=tournament.id)
"""
