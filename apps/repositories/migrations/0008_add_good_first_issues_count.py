from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('repositories', '0007_beginnerchatsession_chatmessage'),
    ]

    operations = [
        migrations.AddField(
            model_name='repository',
            name='good_first_issues_count',
            field=models.IntegerField(default=0),
        ),
    ]
