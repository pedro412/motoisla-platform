from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.audit.services import record_audit
from apps.catalog.models import MediaAsset, MediaAssetStatus, MediaProvider
from apps.catalog.r2 import delete_object_if_exists


class Command(BaseCommand):
    help = "Purge soft-deleted media assets whose retention window already expired."

    def handle(self, *args, **options):
        now = timezone.now()
        assets = MediaAsset.objects.filter(status=MediaAssetStatus.SOFT_DELETED, delete_after__lte=now)
        total = assets.count()
        deleted_count = 0

        for asset in assets.iterator():
            if asset.provider == MediaProvider.R2:
                delete_object_if_exists(asset.object_key_original)
                delete_object_if_exists(asset.object_key_thumb)

            asset_id = asset.id
            provider = asset.provider
            asset.delete()
            deleted_count += 1

            record_audit(
                actor=None,
                action="media.purge",
                entity_type="media_asset",
                entity_id=asset_id,
                payload={"provider": provider},
            )

        self.stdout.write(self.style.SUCCESS(f"Purged {deleted_count}/{total} media assets."))
