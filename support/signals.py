from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from .models import TicketMessage

@receiver(post_delete, sender=TicketMessage)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding `TicketMessage` object is deleted.
    """
    if instance.attachment:
        instance.attachment.delete(save=False)

@receiver(pre_save, sender=TicketMessage)
def auto_delete_file_on_change(sender, instance, **kwargs):
    """
    Deletes old file from filesystem
    when corresponding `TicketMessage` object is updated
    with new file.
    """
    if not instance.pk:
        return False

    try:
        old_file = TicketMessage.objects.get(pk=instance.pk).attachment
    except TicketMessage.DoesNotExist:
        return False

    new_file = instance.attachment
    if not old_file == new_file:
        if old_file:
            old_file.delete(save=False)
