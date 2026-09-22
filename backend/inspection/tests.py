from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from inspection.models import DeclineEvent, DeclineSetting, Inspection


def post_reading(client, code, cd):
    return client.post(
        reverse("create"),
        {
            "aid_code": code,
            "measured_cd": str(cd),
            "required_cd": "1200",
            "bearing_error_deg": "0.2",
        },
    )


class DeclineFlowTests(TestCase):
    def setUp(self):
        group = Group.objects.create(name="inspector")
        self.keeper = User.objects.create_user("keeper", password="light123456")
        self.keeper.groups.add(group)
        self.watch = User.objects.create_user("watch", password="watch123456")
        DeclineSetting.objects.create(drop_cd=50.0, updated_by="system")

    def login(self, username, password):
        self.client.login(username=username, password=password)

    def test_darker_reading_marks_chain_and_logs_event(self):
        self.login("keeper", "light123456")
        post_reading(self.client, "LH-01", 1400)
        post_reading(self.client, "LH-01", 1300)

        event = DeclineEvent.objects.get()
        self.assertEqual(event.aid_code, "LH-01")
        self.assertEqual(event.prev_reading.measured_cd, 1400)
        self.assertEqual(event.curr_reading.measured_cd, 1300)
        self.assertEqual(event.threshold_cd, 50.0)
        self.assertEqual(event.drop_cd, 100.0)

        chain = self.client.get(reverse("chain", args=["LH-01"]))
        self.assertContains(chain, "走低")
        self.assertContains(chain, "100")

        events_page = self.client.get(reverse("events"))
        self.assertContains(events_page, "#%d" % event.prev_reading_id)
        self.assertContains(events_page, "#%d" % event.curr_reading_id)
        self.assertContains(events_page, "100")

    def test_small_drop_below_threshold_logs_nothing(self):
        self.login("keeper", "light123456")
        post_reading(self.client, "LH-01", 1400)
        post_reading(self.client, "LH-01", 1370)
        self.assertEqual(DeclineEvent.objects.count(), 0)

    def test_threshold_change_leaves_old_events_untouched(self):
        self.login("keeper", "light123456")
        post_reading(self.client, "LH-01", 1400)
        post_reading(self.client, "LH-01", 1300)
        event = DeclineEvent.objects.get()

        self.client.post(reverse("threshold"), {"drop_cd": "200"})
        self.assertEqual(DeclineSetting.current().drop_cd, 200.0)

        event.refresh_from_db()
        self.assertEqual(event.threshold_cd, 50.0)
        self.assertEqual(event.drop_cd, 100.0)

        events_page = self.client.get(reverse("events"))
        self.assertContains(events_page, "少 100")
        chain = self.client.get(reverse("chain", args=["LH-01"]))
        self.assertContains(chain, "走低")

        # 新门槛下同样掉 100 不再算走低
        post_reading(self.client, "LH-01", 1200)
        self.assertEqual(DeclineEvent.objects.count(), 1)

    def test_watch_is_read_only(self):
        self.login("keeper", "light123456")
        post_reading(self.client, "LH-01", 1400)
        post_reading(self.client, "LH-01", 1300)
        self.client.logout()

        self.login("watch", "watch123456")
        self.assertEqual(self.client.get(reverse("chains")).status_code, 200)
        self.assertEqual(self.client.get(reverse("chain", args=["LH-01"])).status_code, 200)
        self.assertEqual(self.client.get(reverse("events")).status_code, 200)
        self.assertEqual(self.client.get(reverse("threshold")).status_code, 403)
        self.assertEqual(
            self.client.post(reverse("threshold"), {"drop_cd": "10"}).status_code, 403
        )
        self.assertEqual(post_reading(self.client, "LH-01", 1100).status_code, 403)
        self.assertEqual(DeclineSetting.current().drop_cd, 50.0)
        self.assertEqual(Inspection.objects.filter(measured_cd=1100).count(), 0)

    def test_nav_shows_decline_chain_link(self):
        self.login("watch", "watch123456")
        page = self.client.get(reverse("list"))
        self.assertContains(page, "走低链")
