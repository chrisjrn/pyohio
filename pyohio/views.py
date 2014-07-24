from datetime import datetime
import json

from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from django.http import HttpResponse

from symposion.schedule.models import Slot


def json_serializer(obj):
    if isinstance(obj, datetime.time):
        return obj.strftime("%H:%M")
    raise TypeError


def duration(start, end):
    start_dt = datetime.strptime(start.isoformat(), "%H:%M:%S")
    end_dt = datetime.strptime(end.isoformat(), "%H:%M:%S")
    delta = end_dt - start_dt
    return delta.seconds // 60


def schedule_json(request):
    slots = Slot.objects.all().order_by("start")
    protocol = request.META.get('HTTP_X_FORWARDED_PROTO', 'http')
    data = []
    for slot in slots:
        slot_data = {
            "name": slot.content_override.raw if slot.content_override else "Slot",
            "room": ", ".join(room["name"] for room in slot.rooms.values()),
            "rooms": [room["name"] for room in slot.rooms.values()],
            "start": datetime.combine(slot.day.date, slot.start).isoformat(),
            "end": datetime.combine(slot.day.date, slot.end).isoformat(),
            "duration": duration(slot.start, slot.end),
            "kind": slot.kind.label,
            "conf_key": slot.pk,
            "license": "CC BY",  # this should be configurable or a part of the model
        }
        if hasattr(slot.content, "proposal"):
            slot_data.update({
                "name": slot.content.title,
                "authors": [s.name for s in slot.content.speakers()],
                "released": hasattr(slot.content.proposal, "recording_release") and slot.content.proposal.recording_release,
                "contact": [s.email for s in slot.content.speakers()] if request.user.is_staff else ["redacted"],
                "abstract": slot.content.abstract.raw,
                "description": slot.content.description.raw,
                "conf_url": "%s://%s%s" % (
                    protocol,
                    Site.objects.get_current().domain,
                    reverse("schedule_presentation_detail", args=[slot.content.pk])
                ),
            })
        data.append(slot_data)

    return HttpResponse(
        json.dumps({'schedule': data}, default=json_serializer),
        content_type="application/json"
    )
