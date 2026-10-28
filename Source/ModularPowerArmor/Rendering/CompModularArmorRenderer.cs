using System;
using System.Collections.Generic;
using Verse;

namespace ModularPowerArmor
{
    public class CompProperties_ModularArmorRenderer : CompProperties
    {
        public CompProperties_ModularArmorRenderer()
        {
            compClass = typeof(CompModularArmorRenderer);
        }
    }

    /// <summary>
    /// Added to every humanlike race at startup. When the pawn's render tree is built, adds one
    /// node per visual of every modification installed in the armor the pawn is wearing.
    /// The tree is rebuilt whenever apparel or modules change.
    /// </summary>
    public class CompModularArmorRenderer : ThingComp
    {
        public override List<PawnRenderNode> CompRenderNodes()
        {
            if (!(parent is Pawn pawn) || pawn.apparel == null || !ArmorModuleUtility.Settings.renderModuleGraphics)
            {
                return null;
            }
            PawnRenderTree tree = pawn.Drawer?.renderer?.renderTree;
            if (tree == null)
            {
                return null;
            }
            List<PawnRenderNode> nodes = null;
            foreach (CompModularArmor armor in ArmorModuleUtility.WornModularArmor(pawn))
            {
                foreach (Thing module in armor.Modules)
                {
                    List<PawnRenderNodeProperties> nodeProps = ArmorModuleUtility.PropsOf(module)?.RenderNodesFor(armor.Slot);
                    if (nodeProps.NullOrEmpty())
                    {
                        continue;
                    }
                    foreach (PawnRenderNodeProperties props in nodeProps)
                    {
#if !RW_1_5
                        // Not public in 1.5; module nodes only ever go on humanlike pawns anyway.
                        if (!tree.ShouldAddNodeToTree(props))
                        {
                            continue;
                        }
#endif
                        Type nodeClass = props.nodeClass ?? typeof(PawnRenderNode_ArmorModule);
                        PawnRenderNode node = (PawnRenderNode)Activator.CreateInstance(nodeClass, pawn, props, tree);
                        node.apparel = armor.Apparel;
                        if (node is PawnRenderNode_ArmorModule moduleNode)
                        {
                            moduleNode.module = module;
                            moduleNode.host = armor;
                            moduleNode.slot = armor.Slot;
                        }
                        (nodes ?? (nodes = new List<PawnRenderNode>())).Add(node);
                    }
                }
            }
            return nodes;
        }
    }
}
