using System.Collections.Generic;
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

        public PawnRenderNode_ArmorModule(Pawn pawn, PawnRenderNodeProperties props, PawnRenderTree tree)
            : base(pawn, props, tree)
        {
        }

        public PawnRenderNodeProperties_ArmorModule ModuleProps => Props as PawnRenderNodeProperties_ArmorModule;

        public override GraphicMeshSet MeshSetFor(Pawn pawn)
        {
            return slot == ArmorSlot.Helmet
                ? HumanlikeMeshPoolUtility.GetHumanlikeHeadSetForPawn(pawn)
                : HumanlikeMeshPoolUtility.GetHumanlikeBodySetForPawn(pawn);
        }

        public override Graphic GraphicFor(Pawn pawn)
        {
            string path = Props.texPath;
            if (path.NullOrEmpty())
            {
                return null;
            }
            PawnRenderNodeProperties_ArmorModule moduleProps = ModuleProps;
            if (moduleProps != null && moduleProps.bodyTypeTextures && slot == ArmorSlot.Body && pawn.story?.bodyType != null)
            {
                path += "_" + pawn.story.bodyType.defName;
            }
            bool tinted = moduleProps != null && moduleProps.useArmorColor && apparel != null;
            Color color = tinted ? apparel.DrawColor : Color.white;
            Color colorTwo = tinted ? apparel.DrawColorTwo : Color.white;
            // Transparent by default so soft glows (visors, status lights) aren't clipped like they would be by Cutout.
            Shader shader = Props.shaderTypeDef?.Shader ?? (tinted ? ShaderDatabase.CutoutComplex : ShaderDatabase.Transparent);
            return GraphicDatabase.Get<Graphic_Multi>(path, shader, Vector2.one, color, colorTwo);
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
