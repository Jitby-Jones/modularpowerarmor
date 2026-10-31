using System.Collections.Generic;
using RimWorld;
using UnityEngine;
using Verse;

namespace ModularPowerArmor
{
    /// <summary>
    /// Draws one modification's visual on top of the armor piece it is installed in.
    /// Uses the same body or head mesh as apparel, so overlay textures line up with armor textures.
    /// </summary>
    public class PawnRenderNode_ArmorModule : PawnRenderNode
    {
        public Thing module;
        public CompModularArmor host;
        public ArmorSlot slot = ArmorSlot.Body;

        // The tree is rebuilt, module nodes included, whenever apparel changes, so this stays valid.
        private PawnRenderNode hostNode;

        // The last graphic GraphicFor made, so GetMesh can tell whether it has its own west texture.
        private Graphic_Multi moduleGraphic;

        private PawnRenderNode headNode;

        public PawnRenderNode_ArmorModule(Pawn pawn, PawnRenderNodeProperties props, PawnRenderTree tree)
            : base(pawn, props, tree)
        {
        }

        public PawnRenderNodeProperties_ArmorModule ModuleProps => Props as PawnRenderNodeProperties_ArmorModule;

        /// <summary>
        /// The apparel node drawing the armor piece this module is installed in: a sibling normally,
        /// anywhere in the tree for armor that hangs its node elsewhere. Null when nothing draws the
        /// piece (a mod that hides apparel by leaving its node out, for example).
        /// </summary>
        public PawnRenderNode HostNode
        {
            get
            {
                if (hostNode == null && apparel != null)
                {
                    hostNode = FindHost(parent?.children) ?? FindHostInTree(tree?.rootNode);
                }
                return hostNode;
            }
        }

        /// <summary>The pawn's head node (the one tagged Head), or null.</summary>
        public PawnRenderNode HeadNode
        {
            get
            {
                if (headNode == null)
                {
                    headNode = FindTagged(tree?.rootNode, PawnRenderNodeTagDefOf.Head);
                }
                return headNode;
            }
        }

        private static PawnRenderNode FindTagged(PawnRenderNode node, PawnRenderNodeTagDef tag)
        {
            if (node == null)
            {
                return null;
            }
            if (node.Props?.tagDef == tag)
            {
                return node;
            }
            if (node.children == null)
            {
                return null;
            }
            for (int i = 0; i < node.children.Length; i++)
            {
                PawnRenderNode found = FindTagged(node.children[i], tag);
                if (found != null)
                {
                    return found;
                }
            }
            return null;
        }

        private PawnRenderNode FindHost(PawnRenderNode[] nodes)
        {
            if (nodes == null)
            {
                return null;
            }
            for (int i = 0; i < nodes.Length; i++)
            {
                PawnRenderNode node = nodes[i];
                if (node != this && node.apparel == apparel && !(node is PawnRenderNode_ArmorModule))
                {
                    return node;
                }
            }
            return null;
        }

        private PawnRenderNode FindHostInTree(PawnRenderNode node)
        {
            if (node == null)
            {
                return null;
            }
            PawnRenderNode found = FindHost(node.children);
            if (found != null || node.children == null)
            {
                return found;
            }
            for (int i = 0; i < node.children.Length && found == null; i++)
            {
                found = FindHostInTree(node.children[i]);
            }
            return found;
        }

        public override GraphicMeshSet MeshSetFor(Pawn pawn)
        {
            return slot == ArmorSlot.Helmet
                ? HumanlikeMeshPoolUtility.GetHumanlikeHeadSetForPawn(pawn)
                : HumanlikeMeshPoolUtility.GetHumanlikeBodySetForPawn(pawn);
        }

        public override Graphic GraphicFor(Pawn pawn)
        {
            PawnRenderNodeProperties_ArmorModule moduleProps = ModuleProps;
            string bodyType = null;
            if (moduleProps != null && moduleProps.bodyTypeTextures && slot == ArmorSlot.Body)
            {
                bodyType = pawn.story?.bodyType?.defName ?? "Male";
            }
            string path = ArmorModuleArt.Resolve(Props.texPath, host?.Fit, bodyType);
            if (path == null)
            {
                return null;
            }
            // Module art comes with a CutoutComplex mask: the parts painted like the armor's shell
            // (red in the mask) take the armor's color and are dyed together with the armor, while
            // frames, optics and lamps keep their own colors.
            bool tinted = (moduleProps == null || moduleProps.useArmorColor) && apparel != null;
            Color color = tinted ? apparel.DrawColor : Color.white;
            Color colorTwo = tinted ? apparel.DrawColorTwo : Color.white;
            Shader shader = Props.shaderTypeDef?.Shader ?? ShaderDatabase.CutoutComplex;
            moduleGraphic = GraphicDatabase.Get<Graphic_Multi>(path, shader, Vector2.one, color, colorTwo) as Graphic_Multi;
            return moduleGraphic;
        }

        public override Mesh GetMesh(PawnDrawParms parms)
        {
            // The humanlike mesh sets draw the west facing mirrored, which turns the east texture
            // Graphic_Multi stands in for a missing west one into the west view. Art with its own
            // west texture (a module on one side of the pawn, shown from that side) is drawn facing
            // west already, so it takes the unmirrored mesh.
            if (parms.facing == Rot4.West && moduleGraphic != null && !moduleGraphic.WestFlipped)
            {
                return MeshSetFor(parms.pawn)?.MeshAt(Rot4.East);
            }
            return base.GetMesh(parms);
        }

        protected override IEnumerable<Graphic> GraphicsFor(Pawn pawn)
        {
            Graphic graphic = GraphicFor(pawn);
            if (graphic != null)
            {
                yield return graphic;
            }
        }
    }
}
