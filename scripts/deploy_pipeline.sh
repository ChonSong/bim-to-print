#!/usr/bin/env bash
# Full design iteration pipeline.
# Runs: QA → IFC → G-code → Blender render → Copy to web
#
# Usage: ./scripts/deploy_pipeline.sh [--model examples/house_floorplan.json]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
MODEL="${1:-examples/house_floorplan.json}"
MODEL_NAME="$(basename "$MODEL" .json)"
TIMESTAMP="$(date +%H:%M:%S)"

cd "$REPO_DIR"

echo "═══════════════════════════════════════════"
echo "  🏠 Design Iteration Pipeline  $TIMESTAMP"
echo "  Model: $MODEL"
echo "═══════════════════════════════════════════"

# Step 1: QA assessment
echo ""
echo "📐 Step 1/5: QA Assessment"
.venv/bin/python scripts/qa_assess_plan.py "$MODEL" 2>&1 | tail -5
QA_EXIT=$?
if [ $QA_EXIT -ne 0 ]; then
    echo "❌ QA failed — aborting pipeline"
    exit 1
fi

# Step 2: Generate IFC
echo ""
echo "📄 Step 2/5: IFC Generation"
.venv/bin/python scripts/generate_ifc.py "$MODEL" "docs/research/${MODEL_NAME}.ifc"

# Step 3: Generate G-code (bim2print pipeline)
echo ""
echo "🔧 Step 3/5: G-code Generation"
.venv/bin/python -m bim_to_print.cli gh "$MODEL" "docs/research/${MODEL_NAME}.gcode" \
    --layer-height 10 --perimeter-count 2 --infill-pattern lines --infill-density 0.2 2>&1 | tail -5

# Step 4: Generate plan SVG from G-code
echo ""
echo "📊 Step 4/5: SVG Plan Generation"
.venv/bin/python examples/gcode_to_svg.py "docs/research/${MODEL_NAME}.gcode" \
    --plan "docs/research/plan_view.svg" \
    --stack "docs/research/layer_stack.svg"

# Step 5: Blender render
echo ""
echo "🎨 Step 5/5: Blender Render"
.venv/bin/python scripts/blender_render.py --model "$MODEL" --output "docs/research/renders" --samples 64 2>&1 | tail -10

# Copy renders to research dir
cp docs/research/renders/*.png docs/research/ 2>/dev/null || true

echo ""
echo "═══════════════════════════════════════════"
echo "  ✅ Pipeline complete"
echo "  Results:"
echo "    QA:         scripts/qa_assess_plan.py"
echo "    IFC:        docs/research/${MODEL_NAME}.ifc"
echo "    G-code:     docs/research/${MODEL_NAME}.gcode"
echo "    SVG plans:  docs/research/plan_view.svg"
echo "    Renders:    docs/research/renders/"
echo "═══════════════════════════════════════════"
