from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from inspection.models import DeclineEvent, DeclineSetting, Inspection
from inspection.rules import judge, record_decline


def _can_write(user) -> bool:
    return user.groups.filter(name="inspector").exists()


def health(_request):
    from django.http import JsonResponse

    return JsonResponse({"status": "ok", "service": "nav-aid-inspection"})


@require_http_methods(["GET", "POST"])
def login_view(request):
    from django.contrib.auth import authenticate, login

    error = ""
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username", "").strip(),
            password=request.POST.get("password", ""),
        )
        if user is None:
            error = "用户名或密码错误"
        else:
            login(request, user)
            return redirect("list")
    return render(request, "login.html", {"error": error})


def logout_view(request):
    from django.contrib.auth import logout

    logout(request)
    return redirect("login")


@login_required
def list_view(request):
    rows = Inspection.objects.all()
    return render(request, "list.html", {"rows": rows, "can_write": _can_write(request.user)})


@login_required
def detail_view(request, pk):
    row = get_object_or_404(Inspection, pk=pk)
    return render(request, "detail.html", {"row": row})


@login_required
@require_http_methods(["GET", "POST"])
def create_view(request):
    if not _can_write(request.user):
        return HttpResponseForbidden("仅巡检员可登记灯光巡检")
    error = ""
    if request.method == "POST":
        try:
            measured = float(request.POST["measured_cd"])
            required = float(request.POST["required_cd"])
            bearing = float(request.POST["bearing_error_deg"])
            code = request.POST["aid_code"].strip()
            if not code:
                raise ValueError("empty")
        except (KeyError, ValueError):
            error = "请填编号和三项数值"
        else:
            verdict, note = judge(measured, required, bearing)
            prev = Inspection.objects.filter(aid_code=code).first()
            row = Inspection.objects.create(
                aid_code=code,
                measured_cd=measured,
                required_cd=required,
                bearing_error_deg=bearing,
                verdict=verdict,
                note=note,
                created_by=request.user.username,
            )
            record_decline(prev, row)
            return redirect("detail", pk=row.pk)
    return render(request, "form.html", {"error": error})


@login_required
def chain_index_view(request):
    chains = []
    codes = (
        Inspection.objects.values_list("aid_code", flat=True)
        .distinct()
        .order_by("aid_code")
    )
    for code in codes:
        readings = Inspection.objects.filter(aid_code=code)
        chains.append(
            {
                "aid_code": code,
                "count": readings.count(),
                "latest_cd": readings.first().measured_cd,
                "declines": DeclineEvent.objects.filter(aid_code=code).count(),
            }
        )
    return render(request, "chain_index.html", {"chains": chains})


@login_required
def chain_view(request, aid_code):
    readings = Inspection.objects.filter(aid_code=aid_code).order_by("created_at", "id")
    events = {
        event.curr_reading_id: event
        for event in DeclineEvent.objects.filter(aid_code=aid_code)
    }
    rows = [{"row": row, "event": events.get(row.pk)} for row in readings]
    return render(request, "chain.html", {"aid_code": aid_code, "rows": rows})


@login_required
def events_view(request):
    events = DeclineEvent.objects.select_related("prev_reading", "curr_reading")
    return render(
        request,
        "events.html",
        {"events": events, "threshold": DeclineSetting.current()},
    )


@login_required
@require_http_methods(["GET", "POST"])
def threshold_view(request):
    if not _can_write(request.user):
        return HttpResponseForbidden("仅持灯账号可设定走低门槛")
    error = ""
    if request.method == "POST":
        try:
            drop_cd = float(request.POST["drop_cd"])
            if drop_cd < 0:
                raise ValueError("negative")
        except (KeyError, ValueError):
            error = "请填一个非负数值"
        else:
            DeclineSetting.objects.create(
                drop_cd=drop_cd, updated_by=request.user.username
            )
            return redirect("events")
    return render(
        request,
        "threshold.html",
        {"current": DeclineSetting.current(), "error": error},
    )
