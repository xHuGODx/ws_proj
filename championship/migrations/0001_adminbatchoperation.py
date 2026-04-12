from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AdminBatchOperation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(max_length=80)),
                ("target_ref", models.CharField(blank=True, max_length=120)),
                ("summary", models.CharField(max_length=255)),
                ("metadata_json", models.JSONField(blank=True, default=dict)),
                ("apply_sparql", models.TextField()),
                ("rollback_sparql", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("rolled_back_at", models.DateTimeField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="admin_batch_operations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
