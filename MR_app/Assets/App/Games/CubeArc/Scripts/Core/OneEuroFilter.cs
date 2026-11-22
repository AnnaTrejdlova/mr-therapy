using UnityEngine;

namespace CubeArc
{
    /// <summary>
    /// One Euro filter (Casiez et al. 2012) pro Vector3.
    /// Při pomalém pohybu silně vyhlazuje (potlačí chvění detekce markeru),
    /// při rychlém pohybu vyhlazuje málo (malé zpoždění).
    /// </summary>
    public class OneEuroFilter3
    {
        /// <summary>Minimální mezní frekvence [Hz]. Menší = hladší v klidu.</summary>
        public float MinCutoff;
        /// <summary>Jak rychle roste mezní frekvence s rychlostí. Větší = menší zpoždění při pohybu.</summary>
        public float Beta;
        /// <summary>Mezní frekvence pro odhad rychlosti [Hz].</summary>
        public float DerivativeCutoff;

        private bool hasValue;
        private Vector3 value;
        private Vector3 derivative;
        private double lastTime;

        public OneEuroFilter3(float minCutoff = 1.0f, float beta = 2.0f, float derivativeCutoff = 1.0f)
        {
            MinCutoff = minCutoff;
            Beta = beta;
            DerivativeCutoff = derivativeCutoff;
        }

        public bool HasValue => hasValue;
        public Vector3 Value => value;
        /// <summary>Vyhlazená rychlost [jednotky/s].</summary>
        public Vector3 Velocity => derivative;

        public void Reset()
        {
            hasValue = false;
            derivative = Vector3.zero;
        }

        /// <param name="sample">Nové měření.</param>
        /// <param name="time">Čas měření v sekundách (monotónní).</param>
        public Vector3 Filter(Vector3 sample, double time)
        {
            if (!hasValue)
            {
                hasValue = true;
                value = sample;
                derivative = Vector3.zero;
                lastTime = time;
                return value;
            }

            float dt = (float)(time - lastTime);
            if (dt <= 1e-5f) return value; // stejný snímek nebo čas jde pozpátku
            lastTime = time;

            Vector3 rawDerivative = (sample - value) / dt;
            derivative = Vector3.Lerp(derivative, rawDerivative, Alpha(dt, DerivativeCutoff));

            float cutoff = MinCutoff + Beta * derivative.magnitude;
            value = Vector3.Lerp(value, sample, Alpha(dt, cutoff));
            return value;
        }

        private static float Alpha(float dt, float cutoff)
        {
            float tau = 1f / (2f * Mathf.PI * cutoff);
            return 1f / (1f + tau / dt);
        }
    }
}
