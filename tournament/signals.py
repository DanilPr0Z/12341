"""
Сигналы для автоматического создания наград игрокам
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from tournament.models import TournamentParticipant
from users.models import PlayerAchievement
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=TournamentParticipant)
def award_tournament_prizes(sender, instance, created, **kwargs):
    """
    Автоматически создает награды за призовые места в турнире

    Срабатывает при сохранении TournamentParticipant.
    Если установлено призовое место (1, 2, 3), создается PlayerAchievement.
    """
    # Проверяем, что установлено призовое место
    if instance.final_position and instance.final_position <= 3:
        # Проверяем, что турнир завершен
        if instance.tournament.status != 'completed':
            return

        # Получаем или создаем награду
        achievement, was_created = PlayerAchievement.objects.get_or_create(
            user=instance.user,
            achievement_type='tournament_place',
            tournament=instance.tournament,
            defaults={
                'position': instance.final_position,
                'metadata': {
                    'tournament_name': instance.tournament.name,
                    'tournament_format': instance.tournament.format,
                    'date': instance.tournament.start_date.isoformat() if instance.tournament.start_date else None,
                    'participants_count': instance.tournament.participants.count(),
                    'total_points': instance.total_points,
                }
            }
        )

        if was_created:
            logger.info(
                f"Создана награда для {instance.user.username}: "
                f"{instance.final_position} место в турнире '{instance.tournament.name}'"
            )
        else:
            # Обновляем метаданные, если награда уже существовала
            achievement.position = instance.final_position
            achievement.metadata = {
                'tournament_name': instance.tournament.name,
                'tournament_format': instance.tournament.format,
                'date': instance.tournament.start_date.isoformat() if instance.tournament.start_date else None,
                'participants_count': instance.tournament.participants.count(),
                'total_points': instance.total_points,
            }
            achievement.save()
            logger.info(
                f"Обновлена награда для {instance.user.username}: "
                f"{instance.final_position} место в турнире '{instance.tournament.name}'"
            )
