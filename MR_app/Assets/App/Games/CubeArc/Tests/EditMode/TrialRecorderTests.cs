using NUnit.Framework;
using UnityEngine;

namespace CubeArc.Tests
{
    public class TrialRecorderTests
    {
        private static readonly ArcPath Arc = new ArcPath(Vector3.zero, Vector3.forward, 0.25f, startLeft: true);

        /// <summary>Přenese kostku po oblouku za danou dobu, s volitelnou odchylkou v rovině a mimo ni.</summary>
        private static TrialRecorder RunAlongArc(float duration, float outwardOffset = 0f, float depth = 0f, float fps = 60f)
        {
            var rec = new TrialRecorder(Arc, 0.04f, 0f);
            int frames = Mathf.RoundToInt(duration * fps);
            for (int i = 0; i <= frames; i++)
            {
                float t = i / (float)frames;
                Vector3 p = Arc.PointAt(t) + Arc.OutwardAt(t) * outwardOffset + Arc.Forward * depth;
                rec.Tick(i / fps, true, p);
            }
            return rec;
        }

        [Test]
        public void PerfectRun_FollowsArchLength_AndReachesItsTop()
        {
            TrialSummary s = RunAlongArc(5f).BuildSummary();

            Assert.That(s.duration_s, Is.EqualTo(5f).Within(0.02f));
            Assert.That(s.path_ratio, Is.EqualTo(1f).Within(0.01f));
            Assert.That(s.mean_dev_cm, Is.LessThan(0.1f));
            Assert.That(s.corridor_exits, Is.EqualTo(0));
            Assert.That(s.max_progress, Is.EqualTo(1f).Within(0.01f));
            Assert.That(s.stops, Is.EqualTo(0));
            Assert.That(s.max_height_cm, Is.EqualTo(25f).Within(0.1f), "the cube has to be lifted to the top of the arch");
        }

        [Test]
        public void ConstantRadialOffset_IsReportedAsDeviation()
        {
            TrialSummary s = RunAlongArc(5f, outwardOffset: 0.02f).BuildSummary();
            Assert.That(s.mean_dev_cm, Is.EqualTo(2f).Within(0.1f));
            Assert.That(s.max_dev_cm, Is.EqualTo(2f).Within(0.1f));
            Assert.That(s.time_outside_corridor_s, Is.EqualTo(0f));
        }

        [Test]
        public void DriftTowardsPatient_IsDeviation_AndSignedDepth()
        {
            TrialSummary s = RunAlongArc(5f, depth: -0.03f).BuildSummary();
            Assert.That(s.mean_dev_cm, Is.EqualTo(3f).Within(0.1f));
            Assert.That(s.mean_depth_cm, Is.EqualTo(-3f).Within(0.1f));
        }

        [Test]
        public void OffsetBeyondCorridor_CountsOneExitAndTimeOutside()
        {
            TrialSummary s = RunAlongArc(4f, outwardOffset: 0.06f).BuildSummary();
            Assert.That(s.corridor_exits, Is.EqualTo(1));
            Assert.That(s.time_outside_corridor_s, Is.EqualTo(4f).Within(0.05f));
        }

        [Test]
        public void SamplesAreRecordedAtTenHertz_InArchCoordinates()
        {
            TrialSummary s = RunAlongArc(5f).BuildSummary();
            Assert.That(s.samples.Count, Is.InRange(48, 52));
            Assert.That(s.samples[0].Length, Is.EqualTo(4));
            // První vzorek je start vlevo na základně: x = −r, y = 0, z = 0.
            Assert.That(s.samples[0][1], Is.EqualTo(-0.25f).Within(0.001f));
            Assert.That(s.samples[0][2], Is.EqualTo(0f).Within(0.001f));
            Assert.That(s.samples[0][3], Is.EqualTo(0f).Within(0.001f));
        }

        [Test]
        public void PauseMidway_CountsOneStop()
        {
            var rec = new TrialRecorder(Arc, 0.04f, 0f);
            float time = 0f;
            const float dt = 1f / 60f;

            for (float t = 0f; t <= 0.5f; t += 0.01f, time += dt) rec.Tick(time, true, Arc.PointAt(t));
            for (int i = 0; i < 60; i++, time += dt) rec.Tick(time, true, Arc.PointAt(0.5f));
            for (float t = 0.5f; t <= 1f; t += 0.01f, time += dt) rec.Tick(time, true, Arc.PointAt(t));

            Assert.That(rec.BuildSummary().stops, Is.EqualTo(1));
        }

        [Test]
        public void TrackingLoss_IsTimed_AndPathIsNotBridged()
        {
            var rec = new TrialRecorder(Arc, 0.04f, 0f);
            rec.Tick(0f, true, Arc.PointAt(0f));
            rec.Tick(1f, false, Vector3.zero);
            rec.Tick(2f, false, Vector3.zero);
            rec.Tick(2.1f, true, Arc.PointAt(1f));

            TrialSummary s = rec.BuildSummary();
            Assert.That(s.tracking_lost_s, Is.EqualTo(2f).Within(0.01f));
            Assert.That(s.path_length_m, Is.EqualTo(0f), "a jump across a tracking gap must not count as path");
        }

        [Test]
        public void Progress_NeverDecreases()
        {
            var rec = new TrialRecorder(Arc, 0.04f, 0f);
            rec.Tick(0f, true, Arc.PointAt(0.6f));
            rec.Tick(0.1f, true, Arc.PointAt(0.2f));
            Assert.That(rec.MaxProgress, Is.EqualTo(0.6f).Within(0.001f));
        }
    }
}
