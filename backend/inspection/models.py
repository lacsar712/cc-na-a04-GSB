from django.db import models


class Inspection(models.Model):
    aid_code = models.CharField("航标编号", max_length=40)
    measured_cd = models.FloatField("实测光强")
    required_cd = models.FloatField("要求光强")
    bearing_error_deg = models.FloatField("方位偏差")
    verdict = models.CharField("结论", max_length=20)
    note = models.CharField("说明", max_length=200)
    created_by = models.CharField("登记人", max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]


class DeclineThreshold(models.Model):
    """走低门槛：比上一笔低出多少坎德拉算走低。全站一条，改后只影响新判定。"""

    threshold_cd = models.FloatField("走低门槛（坎德拉）")
    updated_by = models.CharField("修改人", max_length=64)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]

    @classmethod
    def current(cls) -> float:
        row = cls.objects.order_by("-id").first()
        return row.threshold_cd if row else 100.0


class DeclineEvent(models.Model):
    """走低事件：判定那一刻的门槛与差额原样落库，以后改门槛不回写。"""

    prev = models.ForeignKey(
        Inspection, verbose_name="上一笔", related_name="+", on_delete=models.CASCADE
    )
    curr = models.ForeignKey(
        Inspection, verbose_name="本笔", related_name="+", on_delete=models.CASCADE
    )
    threshold_cd = models.FloatField("当时门槛（坎德拉）")
    drop_cd = models.FloatField("差额（坎德拉）")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
