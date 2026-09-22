from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from inspection.models import DeclineEvent, DeclineThreshold, Inspection
from inspection.rules import decline_drop, judge


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
            prev = (
                Inspection.objects.filter(aid_code=code)
                .order_by("-id")
                .first()
            )
            row = Inspection.objects.create(
                aid_code=code,
                measured_cd=measured,
                required_cd=required,
                bearing_error_deg=bearing,
                verdict=verdict,
                note=note,
                created_by=request.user.username,
            )
            if prev is not None:
                threshold = DeclineThreshold.current()
                drop = decline_drop(prev.measured_cd, measured, threshold)
                if drop is not None:
                    DeclineEvent.objects.create(
                        prev=prev, curr=row, threshold_cd=threshold, drop_cd=drop
                    )
            return redirect("chain", aid_code=row.aid_code)
    return render(request, "form.html", {"error": error})


@login_required
def chain_index_view(request):
    codes = (
        Inspection.objects.order_by("aid_code")
        .values_list("aid_code", flat=True)
        .distinct()
    )
    return render(request, "chains.html", {"codes": codes})


@login_required
def chain_view(request, aid_code):
    rows = list(Inspection.objects.filter(aid_code=aid_code).order_by("id"))
    events = {e.curr_id: e for e in DeclineEvent.objects.filter(curr__in=rows)}
    lines = [{"row": row, "event": events.get(row.pk)} for row in rows]
    return render(
        request, "chain.html", {"aid_code": aid_code, "lines": lines}
    )


@login_required
def events_view(request):
    events = DeclineEvent.objects.select_related("prev", "curr").all()
    return render(request, "events.html", {"events": events})


@login_required
@require_http_methods(["GET", "POST"])
def threshold_view(request):
    if not _can_write(request.user):
        return HttpResponseForbidden("仅持灯账号可改走低门槛")
    error = ""
    if request.method == "POST":
        try:
            threshold = float(request.POST["threshold_cd"])
            if threshold <= 0:
                raise ValueError("not positive")
        except (KeyError, ValueError):
            error = "请填大于 0 的坎德拉数"
        else:
            DeclineThreshold.objects.create(
                threshold_cd=threshold, updated_by=request.user.username
            )
            return redirect("threshold")
    current = DeclineThreshold.current()
    history = DeclineThreshold.objects.all()[:10]
    return render(
        request,
        "threshold.html",
        {"error": error, "current": current, "history": history},
    )
