from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0006_add_mexicano_game_mode'),
    ]

    operations = [
        migrations.AddField(
            model_name='gameround',
            name='match_number',
            field=models.IntegerField(
                default=1,
                verbose_name='Номер матча в раунде',
                help_text='Порядковый номер матча внутри раунда (для Mexicano с несколькими кортами)'
            ),
        ),
        migrations.AlterUniqueTogether(
            name='gameround',
            unique_together={('booking', 'round_number', 'match_number')},
        ),
    ]
