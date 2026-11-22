using NUnit.Framework;
using UnityEngine;

namespace CubeArc.Tests
{
    public class ArcPathTests
    {
        private const float Eps = 1e-4f;
        private static readonly Vector3 Center = new Vector3(1f, 0.8f, 2f);

        // Pacient se dívá podél +Z: Right = +X, oblouk stojí v rovině XY.
        private static ArcPath LeftStart(float r = 0.3f) => new ArcPath(Center, Vector3.forward, r, startLeft: true);
        private static ArcPath RightStart(float r = 0.3f) => new ArcPath(Center, Vector3.forward, r, startLeft: false);

        private static void AssertClose(Vector3 expected, Vector3 actual)
        {
            Assert.That(Vector3.Distance(expected, actual), Is.LessThan(Eps), $"expected {expected}, got {actual}");
        }

        [Test]
        public void EndpointsOnBase_TopAboveCenter_StartLeft()
        {
            var arc = LeftStart();
            AssertClose(Center + new Vector3(-0.3f, 0f, 0f), arc.Start);
            AssertClose(Center + new Vector3(0f, 0.3f, 0f), arc.Top);
            AssertClose(Center + new Vector3(0.3f, 0f, 0f), arc.End);
        }

        [Test]
        public void EndpointsAreMirrored_StartRight()
        {
            var arc = RightStart();
            AssertClose(Center + new Vector3(0.3f, 0f, 0f), arc.Start);
            AssertClose(Center + new Vector3(0f, 0.3f, 0f), arc.Top);
            AssertClose(Center + new Vector3(-0.3f, 0f, 0f), arc.End);
        }

        [Test]
        public void ArchPlaneIsVertical_AndFacesThePatient()
        {
            var arc = new ArcPath(Center, new Vector3(0f, -0.8f, 0.6f), 0.3f, true);
            AssertClose(Vector3.forward, arc.Forward);
            AssertClose(Vector3.right, arc.Right);
            for (float t = 0f; t <= 1f; t += 0.1f)
                Assert.That(Vector3.Dot(arc.PointAt(t) - Center, arc.Forward), Is.EqualTo(0f).Within(Eps));
        }

        [Test]
        public void Length_IsHalfCircumference()
        {
            Assert.That(LeftStart(0.25f).Length, Is.EqualTo(Mathf.PI * 0.25f).Within(Eps));
        }

        [TestCase(0f)]
        [TestCase(0.25f)]
        [TestCase(0.5f)]
        [TestCase(0.9f)]
        [TestCase(1f)]
        public void PointOnArc_ProjectsToItself(float t)
        {
            var arc = LeftStart();
            ArcProjection p = arc.Project(arc.PointAt(t));
            Assert.That(p.T, Is.EqualTo(t).Within(Eps));
            Assert.That(p.Deviation, Is.LessThan(Eps));
            Assert.That(p.OutsideRange, Is.False);
        }

        [Test]
        public void RadialDeviation_AboveArchIsPositive_BelowIsNegative()
        {
            var arc = LeftStart();

            ArcProjection above = arc.Project(arc.Top + Vector3.up * 0.04f);
            Assert.That(above.RadialDeviation, Is.EqualTo(0.04f).Within(Eps));
            Assert.That(above.Deviation, Is.EqualTo(0.04f).Within(Eps));
            Assert.That(above.T, Is.EqualTo(0.5f).Within(Eps));

            ArcProjection below = arc.Project(arc.Top - Vector3.up * 0.05f);
            Assert.That(below.RadialDeviation, Is.EqualTo(-0.05f).Within(Eps));
        }

        [Test]
        public void DepthOffPlane_CountsAsDeviation()
        {
            var arc = LeftStart();
            ArcProjection p = arc.Project(arc.PointAt(0.3f) + Vector3.forward * 0.03f + arc.OutwardAt(0.3f) * 0.04f);
            Assert.That(p.Depth, Is.EqualTo(0.03f).Within(Eps));
            Assert.That(p.RadialDeviation, Is.EqualTo(0.04f).Within(Eps));
            Assert.That(p.Deviation, Is.EqualTo(0.05f).Within(Eps));
            Assert.That(p.T, Is.EqualTo(0.3f).Within(Eps));
        }

        [Test]
        public void Height_IsLiftAboveBase()
        {
            var arc = LeftStart();
            Assert.That(arc.Project(arc.Top).Height, Is.EqualTo(0.3f).Within(Eps));
            Assert.That(arc.Project(arc.Start).Height, Is.EqualTo(0f).Within(Eps));
        }

        [Test]
        public void PointBelowBaseNearStart_SnapsToStart()
        {
            var arc = LeftStart();
            ArcProjection p = arc.Project(arc.Start + new Vector3(0.02f, -0.01f, 0f));
            Assert.That(p.T, Is.EqualTo(0f));
            Assert.That(p.OutsideRange, Is.True);
            Assert.That(p.Deviation, Is.EqualTo(new Vector2(0.02f, 0.01f).magnitude).Within(Eps));
        }

        [Test]
        public void RestingJustPastTheGoal_CountsAsFinished()
        {
            var arc = LeftStart();
            // Kostka leží na stole kousek za cílem (nepatrně pod základnou kvůli šumu měření).
            ArcProjection p = arc.Project(arc.End + new Vector3(0.01f, -0.002f, 0.01f));
            Assert.That(p.T, Is.EqualTo(1f));
            Assert.That(p.Deviation, Is.LessThan(0.02f));
        }

        [Test]
        public void Tangent_GoesUpFromStart_AcrossTheTop_DownToGoal()
        {
            var arc = LeftStart();
            AssertClose(Vector3.up, arc.TangentAt(0f));
            AssertClose(Vector3.right, arc.TangentAt(0.5f));
            AssertClose(Vector3.down, arc.TangentAt(1f));

            AssertClose(Vector3.left, RightStart().TangentAt(0.5f));
        }

        [Test]
        public void ToLocal_UsesArcAxes()
        {
            var arc = LeftStart();
            AssertClose(new Vector3(0.1f, 0.2f, 0.3f), arc.ToLocal(Center + new Vector3(0.1f, 0.2f, 0.3f)));
        }
    }
}
