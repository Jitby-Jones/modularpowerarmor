using System.Collections.Generic;
using RimWorld;
using UnityEngine;
using Verse;

namespace ModularPowerArmor
{
    /// <summary>
    /// Render node settings for a modification's visual. Everything from vanilla
    /// PawnRenderNodeProperties (texPath, drawData, visibleFacing, shaderTypeDef, ...) works as usual.
    /// A {fit} token in texPath is replaced by the fit of the armor piece the module is installed
    /// in (see ModularArmorTarget.fit), falling back to Marine.
    /// </summary>
    public class PawnRenderNodeProperties_ArmorModule : PawnRenderNodeProperties
    {
        /// <summary>Append _Male, _Female, _Thin, _Fat or _Hulk to texPath, like body apparel textures.</summary>
        public bool bodyTypeTextures;

        /// <summary>
        /// Dye the overlay with the armor's color: with the default CutoutComplex shader, the parts
        /// the texture's mask marks red take the armor's color (the green channel takes its second
        /// color). Turn off for art that keeps its own colors.
        /// </summary>
        public bool useArmorColor = true;

        /// <summary>
        /// Where to draw between the host armor's layer (0) and the next apparel layer above it (1).
        /// Use different values to order several modules on the same piece.
        /// </summary>
        public float layerFraction = 0.5f;

        /// <summary>Per-body-type nudges for overlays that are drawn once and reused for every body type.</summary>
        public List<BodyTypeAdjustment> bodyTypeAdjustments;

        public BodyTypeAdjustment AdjustmentFor(BodyTypeDef bodyType)
        {
            if (bodyTypeAdjustments == null || bodyType == null)
            {
                return null;
            }
            for (int i = 0; i < bodyTypeAdjustments.Count; i++)
            {
                if (bodyTypeAdjustments[i].bodyType == bodyType)
                {
                    return bodyTypeAdjustments[i];
                }
            }
            return null;
        }
    }

    public class BodyTypeAdjustment
    {
        public BodyTypeDef bodyType;

        public Vector2 scale = Vector2.one;

        /// <summary>Added for every facing; the x component is mirrored when facing west.</summary>
        public Vector3 offset;

        public Vector3 offsetNorth;
        public Vector3 offsetSouth;

        /// <summary>Mirrored on the x axis for west.</summary>
        public Vector3 offsetEast;

        public Vector3 OffsetFor(Rot4 facing)
        {
            Vector3 result = offset;
            if (facing == Rot4.North)
            {
                result += offsetNorth;
            }
            else if (facing == Rot4.South)
            {
                result += offsetSouth;
            }
            else
            {
                result += offsetEast;
            }
            if (facing == Rot4.West)
            {
                result.x = -result.x;
            }
            return result;
        }
    }
}
