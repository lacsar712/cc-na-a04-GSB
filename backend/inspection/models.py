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


class DeclineSetting(models.Model):
    """走低门槛：比上一笔低出多少坎德拉算走低。

    每次调整新落一行，主键最大的一行为当前门槛，旧行留底。
    """

    drop_cd = models.FloatField("走低门槛（坎德拉）")
    updated_by = models.CharField("设定人", max_length=64)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    @classmethod
    def current(cls) -> "DeclineSetting":
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create(drop_cd=50.0, updated_by="system")
        return obj


class DeclineEvent(models.Model):
    """一次走低判定：记下前后两笔主键、当时门槛和差额，落定后不再改动。"""

    aid_code = models.CharField("航标编号", max_length=40)
    prev_reading = models.ForeignKey(
        Inspection, verbose_name="上一笔", related_name="+", on_delete=models.PROTECT
    )
    curr_reading = models.ForeignKey(
        Inspection, verbose_name="本笔", related_name="+", on_delete=models.PROTECT
    )
    threshold_cd = models.FloatField("当时门槛（坎德拉）")
    drop_cd = models.FloatField("走低差额（坎德拉）")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
