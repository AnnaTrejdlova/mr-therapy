using NUnit.Framework;
using UnityEngine;

namespace CubeArc.Tests
{
    public class HandGripTests
    {
        private const float Dt = 1f / 30f; // kamera ~30 Hz
        private static readonly Vector3 GripOffset = new Vector3(0f, -0.02f, 0.08f); // kostka kousek před dlaní

        private static Pose HandAt(Vector3 p, float yawDeg = 0f) => new Pose(p, Quaternion.Euler(0f, yawDeg, 0f));
        private static Pose CubeInHand(Pose hand) => new Pose(hand.position + hand.rotation * GripOffset, hand.rotation);

        /// <summary>Ruka nese kostku rovnoměrně daným směrem.</summary>
        private static float Carry(HandGrip grip, float t0, float seconds, Vector3 velocity, out Pose lastHand)
        {
            float t = t0;
            lastHand = default;
            for (; t < t0 + seconds; t += Dt)
            {
                lastHand = HandAt(new Vector3(0f, 1f, 0.4f) + velocity * t, yawDeg: 20f * t);
                grip.ObserveCube(t, CubeInHand(lastHand), true, lastHand);
            }
            return t;
        }

        [Test]
        public void CarriedCube_IsHeld_AndFollowsTheHandWhenHidden()
        {
            var grip = new HandGrip();
            float t = Carry(grip, 0f, 0.6f, new Vector3(0.2f, 0.1f, 0f), out _);
            Assert.That(grip.IsHolding, Is.True);

            // Kostka zmizí, ruka jde dál a otočí se.
            Pose hand = HandAt(new Vector3(0.3f, 1.2f, 0.45f), yawDeg: 45f);
            Assert.That(grip.TryBridge(t + 0.5f, true, hand, out Pose cube), Is.True);
            Assert.That(Vector3.Distance(cube.position, CubeInHand(hand).position), Is.LessThan(0.01f));
            Assert.That(Quaternion.Angle(cube.rotation, hand.rotation), Is.LessThan(1f));
        }

        [Test]
        public void HandHoveringOverRestingCube_IsNotHolding()
        {
            var grip = new HandGrip();
            var cube = new Pose(new Vector3(0f, 0.8f, 0.4f), Quaternion.identity);
            for (float t = 0f; t < 0.6f; t += Dt)
            {
                Pose hand = HandAt(cube.position - GripOffset); // ruka stojí těsně u kostky, nic se nehýbe
                grip.ObserveCube(t, cube, true, hand);
            }
            Assert.That(grip.IsHolding, Is.False, "a still cube must not start following the hand");
            Assert.That(grip.TryBridge(0.7f, true, HandAt(Vector3.zero), out _), Is.False);
        }

        [Test]
        public void HandMovingPastTheCube_IsNotHolding()
        {
            var grip = new HandGrip();
            var cube = new Pose(new Vector3(0f, 0.8f, 0.4f), Quaternion.identity);
            for (float t = 0f; t < 0.6f; t += Dt)
            {
                Pose hand = HandAt(cube.position + new Vector3(-0.1f + t * 0.3f, 0.05f, 0f)); // ruka projede kolem
                grip.ObserveCube(t, cube, true, hand);
            }
            Assert.That(grip.IsHolding, Is.False);
        }

        [Test]
        public void HandFarFromCube_IsNotHolding()
        {
            var grip = new HandGrip();
            for (float t = 0f; t < 0.6f; t += Dt)
            {
                Pose hand = HandAt(new Vector3(t * 0.2f, 1f, 0.4f));
                // kostka se pohybuje stejně, ale 30 cm od ruky
                grip.ObserveCube(t, new Pose(hand.position + Vector3.right * 0.3f, Quaternion.identity), true, hand);
            }
            Assert.That(grip.IsHolding, Is.False);
        }

        [Test]
        public void Bridge_StopsAfterMaxDuration()
        {
            var grip = new HandGrip { MaxBridgeDuration = 3f };
            float t = Carry(grip, 0f, 0.6f, new Vector3(0.2f, 0f, 0f), out Pose hand);
            Assert.That(grip.TryBridge(t + 2.9f, true, hand, out _), Is.True);
            Assert.That(grip.TryBridge(t + 3.1f, true, hand, out _), Is.False);
        }

        [Test]
        public void Bridge_NeedsATrackedHand()
        {
            var grip = new HandGrip();
            float t = Carry(grip, 0f, 0.6f, new Vector3(0.2f, 0f, 0f), out Pose hand);
            Assert.That(grip.TryBridge(t + 0.2f, false, hand, out _), Is.False);
        }

        [Test]
        public void LosingHandTracking_WhileCubeVisible_ClearsTheGrip()
        {
            var grip = new HandGrip();
            float t = Carry(grip, 0f, 0.6f, new Vector3(0.2f, 0f, 0f), out Pose hand);
            grip.ObserveCube(t, CubeInHand(hand), false, hand);
            Assert.That(grip.IsHolding, Is.False);
        }

        [Test]
        public void ShortHistory_IsNotEnough()
        {
            var grip = new HandGrip();
            Carry(grip, 0f, 0.1f, new Vector3(0.3f, 0f, 0f), out _);
            Assert.That(grip.IsHolding, Is.False);
        }
    }
}
