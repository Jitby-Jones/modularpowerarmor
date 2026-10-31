using System.Collections.Generic;
using UnityEngine;
using Verse;

namespace ModularPowerArmor
{
    /// <summary>
    /// Shows a module overlay whenever its armor piece would be shown, and layers it just
    /// above that piece, below whatever apparel layer comes next.
    /// </summary>
    /// <remarks>Called from the parallel pawn rendering pass, so it only reads state.</remarks>
    public class PawnRenderNodeWorker_ArmorModule : PawnRenderNodeWorker
    {
        public override bool CanDrawNow(PawnRenderNode node, PawnDrawParms parms)
        {
            if (!base.CanDrawNow(node, parms) || !ArmorModuleUtility.Settings.renderModuleGraphics)
            {
                return false;
            }
            List<Rot4> facings = node.Props.visibleFacing;
            if (!facings.NullOrEmpty() && !facings.Contains(parms.facing))
            {
                return false;
            }
            if (!(node is PawnRenderNode_ArmorModule moduleNode))
            {
                return false;
            }
            if (moduleNode.slot == ArmorSlot.Helmet)
            {
                if (!parms.flags.FlagSet(PawnRenderFlags.Headgear) || !PawnRenderNodeWorker_Apparel_Head.HeadgearVisible(parms))
                {
                    return false;
                }
            }
            else if (!parms.flags.FlagSet(PawnRenderFlags.Clothes))
            {
                return false;
            }
            // Only while the armor piece itself is drawn, so whatever hides it (hidden headgear,
            // cosmetic and apparel-hiding mods) hides its modules too.
            PawnRenderNode hostNode = moduleNode.HostNode;
            if (hostNode == null || !hostNode.Worker.CanDrawNow(hostNode, parms))
            {
                return false;
            }
#if RW_1_5
            return hostNode.Graphic != null;
#else
            return hostNode.PrimaryGraphic != null;
#endif
        }

        public override float LayerFor(PawnRenderNode node, PawnDrawParms parms)
        {
            PawnRenderNode_ArmorModule moduleNode = node as PawnRenderNode_ArmorModule;
            PawnRenderNode hostNode = moduleNode?.HostNode;
            if (hostNode == null)
            {
                return base.LayerFor(node, parms);
            }
            if (moduleNode.ModuleProps != null && moduleNode.ModuleProps.aboveHead && moduleNode.HeadNode != null)
            {
                return TopLayer(moduleNode.HeadNode, parms) + 1f;
            }
            float hostLayer = hostNode.Worker.LayerFor(hostNode, parms);
            float nextLayer = float.MaxValue;
            PawnRenderNode[] siblings = hostNode.parent?.children ?? node.parent.children;
            for (int i = 0; i < siblings.Length; i++)
            {
                PawnRenderNode sibling = siblings[i];
                if (sibling == hostNode || sibling is PawnRenderNode_ArmorModule)
                {
                    continue;
                }
                float layer = sibling.Worker.LayerFor(sibling, parms);
                if (layer > hostLayer && layer < nextLayer)
                {
                    nextLayer = layer;
                }
            }
            float gap = nextLayer == float.MaxValue ? 1f : nextLayer - hostLayer;
            float fraction = Mathf.Clamp(moduleNode.ModuleProps?.LayerFractionFor(moduleNode.host?.Fit) ?? 0.5f, 0.01f, 0.99f);
            return hostLayer + gap * fraction;
        }

        /// <summary>The highest layer in a node's subtree (the head, its headgear and their modules).</summary>
        private static float TopLayer(PawnRenderNode node, PawnDrawParms parms)
        {
            float top = node.Worker != null ? node.Worker.LayerFor(node, parms) : float.MinValue;
            if (node.children != null)
            {
                for (int i = 0; i < node.children.Length; i++)
                {
                    PawnRenderNode child = node.children[i];
                    if (child is PawnRenderNode_ArmorModule module && module.ModuleProps != null && module.ModuleProps.aboveHead)
                    {
                        continue;
                    }
                    top = Mathf.Max(top, TopLayer(child, parms));
                }
            }
            return top;
        }

        public override Vector3 OffsetFor(PawnRenderNode node, PawnDrawParms parms, out Vector3 pivot)
        {
            Vector3 offset = base.OffsetFor(node, parms, out pivot);
            BodyTypeAdjustment adjustment = AdjustmentFor(node, parms);
            if (adjustment != null)
            {
                offset += adjustment.OffsetFor(parms.facing);
            }
            return offset;
        }

        public override Vector3 ScaleFor(PawnRenderNode node, PawnDrawParms parms)
        {
            Vector3 scale = base.ScaleFor(node, parms);
            BodyTypeAdjustment adjustment = AdjustmentFor(node, parms);
            if (adjustment != null)
            {
                scale.x *= adjustment.scale.x;
                scale.z *= adjustment.scale.y;
            }
            return scale;
        }

        private static BodyTypeAdjustment AdjustmentFor(PawnRenderNode node, PawnDrawParms parms)
        {
            return (node.Props as PawnRenderNodeProperties_ArmorModule)?.AdjustmentFor(parms.pawn?.story?.bodyType);
        }
    }
}
