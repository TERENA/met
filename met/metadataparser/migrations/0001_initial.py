from django.db import migrations, models
import met.metadataparser.models.base
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Dummy',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
            ],
        ),
        migrations.CreateModel(
            name='Entity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('file_url', models.CharField(verbose_name='Metadata url', max_length=1000, blank=True, null=True, help_text='Url to fetch metadata file')),
                ('file', models.FileField(verbose_name='metadata xml file', blank=True, null=True, help_text='if url is set, metadata url will be fetched and replace file value', upload_to='metadata')),
                ('file_id', models.CharField(verbose_name='File ID', max_length=500, blank=True, null=True)),
                ('registration_authority', models.CharField(verbose_name='Registration Authority', max_length=200, blank=True, null=True)),
                ('entityid', models.CharField(verbose_name='EntityID', max_length=200, unique=True, db_index=True)),
                ('name', met.metadataparser.models.base.JSONField(verbose_name='Display Name', max_length=2000, blank=True, null=True)),
                ('certstats', models.CharField(verbose_name='Certificate Stats', max_length=200, blank=True, null=True)),
                ('_display_protocols', models.CharField(verbose_name='Display Protocols', max_length=300, blank=True, null=True)),
                ('editor_users', models.ManyToManyField(verbose_name='editor users', blank=True, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Entity',
                'verbose_name_plural': 'Entities',
            },
        ),
        migrations.CreateModel(
            name='Entity_Federations',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('registration_instant', models.DateField(verbose_name='Registration Instant', blank=True, null=True)),
                ('entity', models.ForeignKey(to='metadataparser.Entity')),
            ],
        ),
        migrations.CreateModel(
            name='EntityCategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('category_id', models.CharField(verbose_name='Entity category ID', max_length=1000, help_text='The ID of the entity category')),
                ('name', models.CharField(verbose_name='Entity category name', max_length=1000, blank=True, null=True, help_text='The name of the entity category')),
            ],
        ),
        migrations.CreateModel(
            name='EntityStat',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('time', models.DateTimeField(verbose_name='Metadata time stamp')),
                ('feature', models.CharField(verbose_name='Feature name', max_length=100, db_index=True)),
                ('value', models.PositiveIntegerField(verbose_name='Feature value')),
            ],
        ),
        migrations.CreateModel(
            name='EntityType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('name', models.CharField(verbose_name='Name', max_length=20, unique=True, db_index=True)),
                ('xmlname', models.CharField(verbose_name='Name in XML', max_length=20, unique=True, db_index=True)),
            ],
        ),
        migrations.CreateModel(
            name='Federation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('file_url', models.CharField(verbose_name='Metadata url', max_length=1000, blank=True, null=True, help_text='Url to fetch metadata file')),
                ('file', models.FileField(verbose_name='metadata xml file', blank=True, null=True, help_text='if url is set, metadata url will be fetched and replace file value', upload_to='metadata')),
                ('file_id', models.CharField(verbose_name='File ID', max_length=500, blank=True, null=True)),
                ('registration_authority', models.CharField(verbose_name='Registration Authority', max_length=200, blank=True, null=True)),
                ('name', models.CharField(verbose_name='Name', max_length=200, unique=True)),
                ('type', models.CharField(verbose_name='Type', max_length=100, blank=True, null=True, choices=[(None, ''), ('hub-and-spoke', 'Hub and Spoke'), ('mesh', 'Full Mesh')])),
                ('url', models.URLField(verbose_name='Federation url', blank=True, null=True)),
                ('fee_schedule_url', models.URLField(verbose_name='Fee schedule url', max_length=150, blank=True, null=True)),
                ('logo', models.ImageField(verbose_name='Federation logo', blank=True, null=True, upload_to='federation_logo')),
                ('is_interfederation', models.BooleanField(verbose_name='Is interfederation', db_index=True, default=False)),
                ('slug', models.SlugField(max_length=200, unique=True)),
                ('country', models.CharField(verbose_name='Country', max_length=100, blank=True, null=True)),
                ('metadata_update', models.DateTimeField(verbose_name='Metadata update date and time', blank=True, null=True)),
                ('certstats', models.CharField(verbose_name='Certificate Stats', max_length=200, blank=True, null=True)),
                ('editor_users', models.ManyToManyField(verbose_name='editor users', blank=True, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='entitystat',
            name='federation',
            field=models.ForeignKey(verbose_name='Federations', to='metadataparser.Federation'),
        ),
        migrations.AddField(
            model_name='entity_federations',
            name='entity_categories',
            field=models.ManyToManyField(verbose_name='Entity categories', to='metadataparser.EntityCategory'),
        ),
        migrations.AddField(
            model_name='entity_federations',
            name='federation',
            field=models.ForeignKey(to='metadataparser.Federation'),
        ),
        migrations.AddField(
            model_name='entity',
            name='federations',
            field=models.ManyToManyField(verbose_name='Federations', to='metadataparser.Federation', through='metadataparser.Entity_Federations'),
        ),
        migrations.AddField(
            model_name='entity',
            name='types',
            field=models.ManyToManyField(verbose_name='Type', to='metadataparser.EntityType'),
        ),
    ]
