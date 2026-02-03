"""
Django Admin для турнирной системы
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Tournament, PadelTeam, TournamentParticipant, TournamentMatch, TournamentRound


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    """Админка для турниров"""

    list_display = [
        'name',
        'format_display',
        'start_date',
        'status_badge',
        'participants_info',
        'entry_fee',
        'prize_pool',
        'organizer'
    ]

    list_filter = [
        'status',
        'format',
        'is_team_tournament',
        'is_mixed',
        'start_date'
    ]

    search_fields = [
        'name',
        'description',
        'organizer__username',
        'organizer__first_name',
        'organizer__last_name'
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
        'participants_count',
        'available_slots'
    ]

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'organizer', 'image')
        }),
        ('Даты', {
            'fields': ('start_date', 'end_date', 'registration_deadline')
        }),
        ('Формат турнира', {
            'fields': (
                'format',
                'is_team_tournament',
                'is_mixed',
                'points_per_match'
            )
        }),
        ('Участники', {
            'fields': (
                'max_participants',
                'participants_count',
                'available_slots',
                'min_rating',
                'max_rating'
            )
        }),
        ('Финансы', {
            'fields': ('entry_fee', 'prize_pool')
        }),
        ('Статус', {
            'fields': ('status',)
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def format_display(self, obj):
        """Отображение формата с иконкой"""
        icons = {
            'americano': '🔄',
            'mexicano': '📊',
            'mixed_americano': '⚖️',
            'team_americano': '👥',
            'team_mexicano': '👥📊',
            'doubles_elimination': '🏆',
            'doubles_round_robin': '⭕',
        }
        icon = icons.get(obj.format, '🎾')
        return f"{icon} {obj.get_format_display()}"
    format_display.short_description = 'Формат'

    def status_badge(self, obj):
        """Цветной бейдж статуса"""
        colors = {
            'draft': 'gray',
            'registration_open': 'green',
            'registration_closed': 'orange',
            'in_progress': 'blue',
            'completed': 'purple',
            'cancelled': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Статус'

    def participants_info(self, obj):
        """Информация об участниках"""
        count = obj.participants_count
        max_p = obj.max_participants
        percentage = (count / max_p * 100) if max_p > 0 else 0

        color = 'green' if percentage < 70 else 'orange' if percentage < 100 else 'red'

        return format_html(
            '<div style="width: 100px;"><div style="background-color: #f0f0f0; border-radius: 5px; overflow: hidden;">'
            '<div style="background-color: {}; width: {}%; height: 20px; display: flex; align-items: center; justify-content: center; color: white; font-size: 10px;">'
            '{}/{}'
            '</div></div></div>',
            color,
            percentage,
            count,
            max_p
        )
    participants_info.short_description = 'Участники'


@admin.register(PadelTeam)
class PadelTeamAdmin(admin.ModelAdmin):
    """Админка для пар"""

    list_display = [
        'display_name_short',
        'tournament',
        'is_temporary',
        'round_number',
        'seed'
    ]

    list_filter = [
        'is_temporary',
        'tournament__name',
        'round_number'
    ]

    search_fields = [
        'name',
        'player1__username',
        'player1__first_name',
        'player1__last_name',
        'player2__username',
        'player2__first_name',
        'player2__last_name',
        'tournament__name'
    ]

    readonly_fields = ['created_at', 'players_list']

    fieldsets = (
        ('Турнир', {
            'fields': ('tournament',)
        }),
        ('Игроки', {
            'fields': ('player1', 'player2', 'players_list')
        }),
        ('Настройки', {
            'fields': ('name', 'seed', 'is_temporary', 'round_number')
        }),
        ('Метаданные', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def display_name_short(self, obj):
        """Короткое отображение названия"""
        return str(obj)[:50]
    display_name_short.short_description = 'Пара'

    def players_list(self, obj):
        """Список игроков в паре"""
        return format_html(
            '<ul><li>{}</li><li>{}</li></ul>',
            obj.player1.get_full_name() or obj.player1.username,
            obj.player2.get_full_name() or obj.player2.username
        )
    players_list.short_description = 'Игроки'


@admin.register(TournamentParticipant)
class TournamentParticipantAdmin(admin.ModelAdmin):
    """Админка для участников"""

    list_display = [
        'user',
        'tournament',
        'payment_status_badge',
        'total_points',
        'matches_info',
        'win_rate_display',
        'current_rank',
        'registered_at'
    ]

    list_filter = [
        'payment_status',
        'tournament__name',
        'registered_at'
    ]

    search_fields = [
        'user__username',
        'user__first_name',
        'user__last_name',
        'user__email',
        'tournament__name',
        'team_name'
    ]

    readonly_fields = [
        'registered_at',
        'win_rate',
        'average_points_per_match'
    ]

    fieldsets = (
        ('Участник', {
            'fields': ('tournament', 'user')
        }),
        ('Для командных турниров', {
            'fields': ('partner', 'team_name', 'seed'),
            'classes': ('collapse',)
        }),
        ('Статистика (Americano/Mexicano)', {
            'fields': (
                'total_points',
                'matches_played',
                'matches_won',
                'matches_lost',
                'current_rank',
                'win_rate',
                'average_points_per_match'
            )
        }),
        ('Оплата', {
            'fields': ('payment_status', 'payment_date')
        }),
        ('Результат', {
            'fields': ('final_position',)
        }),
        ('Метаданные', {
            'fields': ('registered_at',),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_paid']

    def payment_status_badge(self, obj):
        """Цветной бейдж статуса оплаты"""
        colors = {
            'pending': 'orange',
            'paid': 'green',
            'refunded': 'red',
        }
        color = colors.get(obj.payment_status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_payment_status_display()
        )
    payment_status_badge.short_description = 'Оплата'

    def matches_info(self, obj):
        """Информация о матчах"""
        return f"{obj.matches_played} ({obj.matches_won}W/{obj.matches_lost}L)"
    matches_info.short_description = 'Матчи'

    def win_rate_display(self, obj):
        """Процент побед"""
        wr = obj.win_rate
        color = 'green' if wr >= 50 else 'orange' if wr >= 30 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color,
            wr
        )
    win_rate_display.short_description = 'Win Rate'

    def mark_as_paid(self, request, queryset):
        """Отметить как оплаченные"""
        count = 0
        for participant in queryset:
            participant.mark_as_paid()
            count += 1
        self.message_user(request, f'{count} участников отмечено как оплачено')
    mark_as_paid.short_description = 'Отметить как оплачено'


@admin.register(TournamentMatch)
class TournamentMatchAdmin(admin.ModelAdmin):
    """Админка для матчей"""

    list_display = [
        'match_info',
        'tournament',
        'round',
        'teams_display',
        'score_display_badge',
        'status_badge',
        'scheduled_info'
    ]

    list_filter = [
        'status',
        'tournament__name',
        'round',
        'scheduled_date'
    ]

    search_fields = [
        'tournament__name',
        'team1__player1__username',
        'team1__player2__username',
        'team2__player1__username',
        'team2__player2__username'
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
        'is_ready_to_play',
        'score_display'
    ]

    fieldsets = (
        ('Турнир', {
            'fields': ('tournament', 'round', 'match_number')
        }),
        ('Пары', {
            'fields': ('team1', 'team2', 'winning_team', 'is_ready_to_play')
        }),
        ('Счет', {
            'fields': (
                'score_team1',
                'score_team2',
                'detailed_score',
                'score_display'
            )
        }),
        ('Расписание', {
            'fields': ('scheduled_date', 'scheduled_time', 'court')
        }),
        ('Статус и связи', {
            'fields': ('status', 'next_match')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def match_info(self, obj):
        """Информация о матче"""
        return f"R{obj.round} M{obj.match_number}"
    match_info.short_description = 'Раунд/Матч'

    def teams_display(self, obj):
        """Отображение пар"""
        team1_name = str(obj.team1)[:30] if obj.team1 else 'TBD'
        team2_name = str(obj.team2)[:30] if obj.team2 else 'TBD'
        return format_html(
            '<div><strong>{}</strong> vs <strong>{}</strong></div>',
            team1_name,
            team2_name
        )
    teams_display.short_description = 'Пары'

    def score_display_badge(self, obj):
        """Отображение счета с выделением победителя"""
        if obj.status != 'completed':
            return '-'

        team1_style = 'font-weight: bold; color: green;' if obj.winning_team == obj.team1 else ''
        team2_style = 'font-weight: bold; color: green;' if obj.winning_team == obj.team2 else ''

        return format_html(
            '<span style="{}">{}</span> - <span style="{}">{}</span>',
            team1_style,
            obj.score_team1,
            team2_style,
            obj.score_team2
        )
    score_display_badge.short_description = 'Счет'

    def status_badge(self, obj):
        """Цветной бейдж статуса"""
        colors = {
            'scheduled': 'blue',
            'in_progress': 'orange',
            'completed': 'green',
            'walkover': 'gray',
            'cancelled': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Статус'

    def scheduled_info(self, obj):
        """Информация о расписании"""
        if obj.scheduled_date and obj.scheduled_time:
            return f"{obj.scheduled_date} {obj.scheduled_time.strftime('%H:%M')}"
        elif obj.scheduled_date:
            return str(obj.scheduled_date)
        return '-'
    scheduled_info.short_description = 'Расписание'


@admin.register(TournamentRound)
class TournamentRoundAdmin(admin.ModelAdmin):
    """Админка для раундов"""

    list_display = [
        'tournament',
        'round_number',
        'name',
        'matches_count',
        'completed_matches_count',
        'progress_bar',
        'is_completed',
        'start_date'
    ]

    list_filter = [
        'is_completed',
        'tournament__name',
        'start_date'
    ]

    search_fields = [
        'tournament__name',
        'name'
    ]

    readonly_fields = [
        'matches_count',
        'completed_matches_count',
        'completion_percentage'
    ]

    fieldsets = (
        ('Турнир и раунд', {
            'fields': ('tournament', 'round_number', 'name')
        }),
        ('Прогресс', {
            'fields': (
                'is_completed',
                'matches_count',
                'completed_matches_count',
                'completion_percentage'
            )
        }),
        ('Расписание', {
            'fields': ('start_date',)
        }),
    )

    def progress_bar(self, obj):
        """Прогресс-бар завершения раунда"""
        percentage = obj.completion_percentage
        color = 'orange' if percentage < 100 else 'green'

        return format_html(
            '<div style="width: 150px;">'
            '<div style="background-color: #f0f0f0; border-radius: 5px; overflow: hidden;">'
            '<div style="background-color: {}; width: {}%; height: 20px; display: flex; align-items: center; justify-content: center; color: white; font-size: 11px;">'
            '{:.0f}%'
            '</div></div></div>',
            color,
            percentage,
            percentage
        )
    progress_bar.short_description = 'Прогресс'
