import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Preformatted
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

# Define custom canvas for two-pass page numbering and running headers/footers
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            # Draw decorative elements on Cover Page
            self.saveState()
            # Left accent color block (dark blue)
            self.setFillColor(HexColor('#0f172a'))
            self.rect(0, 0, 18, 792, fill=1, stroke=0)
            # Cyan strip accent
            self.setFillColor(HexColor('#38bdf8'))
            self.rect(18, 0, 6, 792, fill=1, stroke=0)
            self.restoreState()
            return

        # Running Header/Footer for content pages
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(HexColor('#475569'))
        
        # Header text and thin rules
        self.drawString(54, 746, "A-LIFE PAC-MAN SIMULATION ARCHITECTURE")
        self.drawRightString(558, 746, "TECHNICAL REFERENCE MANUAL")
        self.setStrokeColor(HexColor('#cbd5e1'))
        self.setLineWidth(0.5)
        self.line(54, 738, 558, 738)
        
        # Footer text, rules and page numbers
        self.line(54, 52, 558, 52)
        self.setFont("Helvetica", 8)
        self.drawString(54, 38, "Confidential - Artificial Life & Evolutionary AI Research Group")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 38, page_text)
        self.restoreState()

def build_pdf():
    pdf_filename = "A_Life_Pacman_Architecture.pdf"
    
    # 54pt margin = 0.75 in. Printable width = 612 - 108 = 504pt
    # topMargin/bottomMargin = 72pt (1 in) to clear header/footer lines at Y=738 and Y=52
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=72,
        bottomMargin=72
    )

    styles = getSampleStyleSheet()
    
    # Define professional color palette
    c_primary = HexColor('#0f172a')     # Dark slate
    c_secondary = HexColor('#1e293b')   # Slate
    c_accent = HexColor('#0284c7')      # Ocean Blue
    c_body = HexColor('#334155')        # Charcoal
    c_code_bg = HexColor('#f8fafc')     # Light gray
    c_code_border = HexColor('#cbd5e1') # Muted border
    
    # Custom typography styles
    style_title = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=26,
        leading=32,
        textColor=c_primary,
        spaceAfter=10
    )
    
    style_subtitle = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=13,
        leading=17,
        textColor=c_accent,
        spaceAfter=30
    )
    
    style_h1 = ParagraphStyle(
        'ChapterH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=c_primary,
        spaceBefore=22,
        spaceAfter=12,
        keepWithNext=True
    )

    style_h2 = ParagraphStyle(
        'SectionH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=c_secondary,
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )
    
    style_body = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=c_body,
        spaceAfter=8
    )

    style_list = ParagraphStyle(
        'ListDark',
        parent=style_body,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )

    style_code = ParagraphStyle(
        'CodeMonospace',
        fontName='Courier',
        fontSize=8,
        leading=10.5,
        textColor=HexColor('#0f172a')
    )

    def code_block(code_str):
        # Cleans double newlines at boundaries
        code_str = code_str.strip('\n')
        pre = Preformatted(code_str, style_code)
        tbl = Table([[pre]], colWidths=[504])
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), c_code_bg),
            ('BOX', (0,0), (-1,-1), 0.5, c_code_border),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING', (0,0), (-1,-1), 12),
            ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ]))
        return tbl

    story = []

    # ==========================================
    # COVER PAGE
    # ==========================================
    story.append(Spacer(1, 140))
    story.append(Paragraph("A-Life Pac-Man", style_title))
    story.append(Paragraph("Ecosystem Architecture, Evolutionary Neural Networks, and Decoupled Agency", style_subtitle))
    
    # Cyan line separator
    separator_line = Table([['']], colWidths=[180], rowHeights=[3])
    separator_line.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_accent),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(separator_line)
    story.append(Spacer(1, 20))
    
    metadata_text = """
    <b>Prepared For:</b> Advanced Agentic Coding Research Review<br/>
    <b>Author:</b> Antigravity AI Engineering Division<br/>
    <b>Date:</b> May 2026<br/>
    <b>Status:</b> Published Technical Guide<br/>
    <b>Document Version:</b> 1.4.0
    """
    story.append(Paragraph(metadata_text, style_body))
    story.append(PageBreak())

    # ==========================================
    # TABLE OF CONTENTS
    # ==========================================
    story.append(Paragraph("Table of Contents", style_h1))
    story.append(Spacer(1, 10))
    
    toc_data = [
        ["Chapter 1: Executive Overview & Simulation Core", "Page 3"],
        ["Chapter 2: PyTorch Neural Network Brain (brain.py)", "Page 4"],
        ["Chapter 3: Cognitive Control & Instinct Drives (soul.py)", "Page 5"],
        ["Chapter 4: Physical Bodies, Development & Locomotion (entity.py)", "Page 6"],
        ["Chapter 5: World Simulation Grid, Navigation & Social Systems (world.py)", "Page 7"],
        ["Chapter 6: Dynamic Vector Rendering (ui.py)", "Page 8"],
    ]
    
    toc_table = Table(toc_data, colWidths=[400, 104])
    toc_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0,0), (-1,-1), c_body),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LINEBELOW', (0,0), (-1,-1), 0.25, HexColor('#e2e8f0')),
    ]))
    story.append(toc_table)
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 1: OVERVIEW
    # ==========================================
    story.append(Paragraph("Chapter 1: Executive Overview & Simulation Core", style_h1))
    story.append(Paragraph(
        "The A-Life Pac-Man project is a bio-inspired evolutionary neural network simulation that merges visual "
        "game mechanics with complex cognitive agent behaviors. Unlike traditional Pac-Man where entities "
        "rely on deterministic state machines or static pathing trees, this system models two competing species "
        "('spots' and 'stripes') whose behaviors are governed by independent feedforward neural networks. Over "
        "successive generations, these weights undergo selection pressure based on foraging efficiency, base defense, "
        "and mate attraction.", style_body
    ))
    story.append(Paragraph(
        "The primary design pillars of the simulation include:", style_body
    ))
    story.append(Paragraph("• <b>Decoupled Architecture</b>: Physical simulation loops, visual render pipelines, "
                           "and agent mind controllers ('souls') are strictly decoupled. This allows headless execution, "
                           "independent testing, and modular extensions.", style_list))
    story.append(Paragraph("• <b>Genetic Evolution</b>: A double-pass crossover mechanism combined with gaussian mutation "
                           "operates directly on neural parameter weights. Fitness points are dynamically awarded based on "
                           "productive tasks (storing food, defending bases, reproducing).", style_list))
    story.append(Paragraph("• <b>Day/Night & Curse Cycle</b>: Environmental variations force temporal behaviors. Day cycles "
                           "focus on productivity and foraging. Night cycles trigger zombie invasions, introducing survival "
                           "pressures and curfew enforcement.", style_list))
    story.append(Paragraph("• <b>Hardware Acceleration</b>: Tensors representing neural connections are mapped directly onto "
                           "accelerated system frameworks (such as Apple Silicon's MPS or NVIDIA CUDA) via PyTorch.", style_list))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 2: BRAIN.PY
    # ==========================================
    story.append(Paragraph("Chapter 2: PyTorch Neural Network Brain (brain.py)", style_h1))
    story.append(Paragraph(
        "The <b>Brain</b> class represents the cognitive hardware of an entity. It is structured as a two-layer "
        "fully connected feedforward neural network with 7 input nodes, 12 hidden nodes, and 6 output nodes. "
        "Weights are stored as PyTorch float32 tensors, enabling accelerated tensor multiplications.", style_body
    ))
    story.append(Paragraph(
        "<b>Sensory Inputs (7 dimensions):</b>", style_body
    ))
    story.append(Paragraph("1. <i>Proximity to Food</i>: 1.0 / (1.0 + distance to nearest mushroom or worm).", style_list))
    story.append(Paragraph("2. <i>Proximity to Castle</i>: 1.0 / (1.0 + distance to species' home base).", style_list))
    story.append(Paragraph("3. <i>Proximity to Enemy</i>: Proximity value to closest adult of the opposite species.", style_list))
    story.append(Paragraph("4. <i>Proximity to Mate</i>: Proximity value to closest compatible mate with inactive mating cooldown.", style_list))
    story.append(Paragraph("5. <i>Energy Level</i>: Current physical energy scaled [0.0 - 1.0].", style_list))
    story.append(Paragraph("6. <i>Age Ratio</i>: Current lifespan relative to world life expectancy.", style_list))
    story.append(Paragraph("7. <i>Reserves Level</i>: Current food reserves stored in the home base scaled by maximum storage capacity.", style_list))
    
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>Output Actions (6 dimensions):</b>", style_body))
    story.append(Paragraph("The output vector uses a <i>tanh</i> activation function, representing drive strength [-1.0, 1.0] for the six actions: "
                           "<b>Forage</b>, <b>Store</b>, <b>Attack</b>, <b>Mate</b>, <b>Cultivate (Plant)</b>, and <b>Defend (Guard)</b>.", style_body))

    story.append(Paragraph("The neural feedforward operation maps inputs directly onto device weights using PyTorch:", style_body))
    
    brain_feed_forward_code = """
class Brain:
    def __init__(self, input_size=7, hidden_size=12, output_size=6, weights=None):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size
        
        if weights is not None:
            self.w1 = weights['w1'].clone().to(DEVICE)
            self.w2 = weights['w2'].clone().to(DEVICE)
        else:
            self.w1 = (torch.rand((input_size, hidden_size), dtype=torch.float32, device=DEVICE) * 2.0 - 1.0)
            self.w2 = (torch.rand((hidden_size, output_size), dtype=torch.float32, device=DEVICE) * 2.0 - 1.0)

    def feed_forward(self, inputs_list):
        inputs_tensor = torch.tensor(inputs_list, dtype=torch.float32, device=DEVICE)
        hidden = torch.tanh(torch.matmul(inputs_tensor, self.w1))
        outputs = torch.tanh(torch.matmul(hidden, self.w2))
        return {
            'hidden': hidden.cpu().numpy(),
            'outputs': outputs.cpu().numpy()
        }
    """
    story.append(code_block(brain_feed_forward_code))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 3: SOUL.PY
    # ==========================================
    story.append(Paragraph("Chapter 3: Cognitive Control & Instinct Drives (soul.py)", style_h1))
    story.append(Paragraph(
        "The <b>Soul</b> acts as the decoupled controller of the physical Pac-Man body. It polls the physical coordinates "
        "and the world environment, compiles the 7 normalized inputs, queries the `Brain` feedforward network, and resolves "
        "drives. It also applies crucial biological and environmental rules that override neural defaults during critical states.", style_body
    ))
    
    story.append(Paragraph("<b>Heuristic Instinct Overrides:</b>", style_h2))
    story.append(Paragraph("• <b>Virgin Mating Drive</b>: Young adults who have not yet passed on their genetics receive a "
                           "temporary mating drive boost (+0.85) to encourage genetic continuation.", style_list))
    story.append(Paragraph("• <b>Female Protection</b>: Males near friendly females who are threatened by rival males "
                           "have their Attack output boosted (+1.5) to engage in defense.", style_list))
    story.append(Paragraph("• <b>Extinction Avoidance</b>: If a species' population falls below 3, mating drives are heavily "
                           "boosted (+1.5) to prevent total collapse.", style_list))
    story.append(Paragraph("• <b>Resource Delivery Lock</b>: If carrying food, carrying a baby, or carrying a worm, the active "
                           "drive is locked to 'Store' to ensure base safety and development.", style_list))

    story.append(Paragraph("The drive decision logic from `soul.py` operates as follows:", style_body))
    
    soul_decision_code = """
# Choose highest output drive
drives = ["Forage", "Store", "Attack", "Mate", "Cultivate", "Defend"]
max_val = -float('inf')
max_drive_index = 0

for i, drive in enumerate(drives):
    val = outputs[i]
    # Restriction on infants and old age: no attack (2), mate (3), or cultivate (4)
    if body.is_infant() or body.is_old():
        if i in [2, 3, 4]:
            continue
    if val > max_val:
        max_val = val
        max_drive_index = i

body.current_drive = drives[max_drive_index]

# Force 'Store' drive under carrying rules
if body.food_carried > 0 or getattr(body, 'has_worm', False) or getattr(body, 'carrying_baby', None) is not None or rescue_target is not None:
    if body.current_drive not in ["Store", "Cultivate"]:
        body.current_drive = "Store"
    """
    story.append(code_block(soul_decision_code))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 4: ENTITY.PY
    # ==========================================
    story.append(Paragraph("Chapter 4: Physical Bodies, Development & Locomotion (entity.py)", style_h1))
    story.append(Paragraph(
        "Physical simulation metrics are maintained inside the `Pacman` class in `entity.py`. "
        "A Pacman possesses position coordinates, velocity glide factors, energy pools, and developmental age brackets. "
        "Unlike basic grid systems where entities instantly teleport between tiles, Pacman entities glide smoothly, "
        "calculating intermediate coordinate states per simulation tick.", style_body
    ))
    
    story.append(Paragraph("<b>Developmental Stages:</b>", style_h2))
    story.append(Paragraph("• <b>Infancy</b>: Less than 10% of total lifespan. Cannot mate, plant, or attack. Energy loss "
                           "is reduced, and they automatically feed from home base reserves to grow.", style_list))
    story.append(Paragraph("• <b>Adulthood</b>: 10% to 90% of lifespan. Capable of all drives. Energy loss is standard.", style_list))
    story.append(Paragraph("• <b>Senescence (Old Age)</b>: Greater than 90% of lifespan. Speed is reduced by 40%. "
                           "Cannot mate or plant. Typically act as castle defenders, blocking gates against hostile thieves.", style_list))
    
    story.append(Spacer(1, 4))
    story.append(Paragraph("Locomotion speed modifiers apply based on current state (e.g. holding cargo slows movement by 15%):", style_body))

    entity_move_code = """
def move(self):
    if self.carried_by is not None:
        self.x = self.carried_by.x
        self.y = self.carried_by.y
        return

    if not self.target_tile:
        return

    dx = self.target_tile['x'] - self.x
    dy = self.target_tile['y'] - self.y
    dist = math.sqrt(dx*dx + dy*dy)

    # Base speed & modifiers
    current_speed = self.speed
    if self.is_old():
        current_speed = self.speed * 0.6
    elif self.is_infant():
        current_speed = self.speed * 0.65
    
    if self.food_carried > 0 or self.has_worm:
        current_speed *= 0.85

    if dist <= current_speed:
        self.x = float(self.target_tile['x'])
        self.y = float(self.target_tile['y'])
        self.tile_x = self.target_tile['x']
        self.tile_y = self.target_tile['y']
        self.check_target_interaction()
        
        if len(self.current_path) > 0:
            self.target_tile = self.current_path.pop(0)
        else:
            self.target_tile = None
    else:
        self.x += (dx / dist) * current_speed
        self.y += (dy / dist) * current_speed
    """
    story.append(code_block(entity_move_code))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 5: WORLD.PY
    # ==========================================
    story.append(Paragraph("Chapter 5: World Grid, Navigation & Social Systems (world.py)", style_h1))
    story.append(Paragraph(
        "The **SimulationWorld** manages grid coordinates, resource spawning, time-of-day cycles, "
        "and physical interaction resolvers (combat, mating, mentoring). The grid maps a custom "
        "47x21 layout containing a structured maze (columns 0-26), a partitioned division wall with gates (column 27), "
        "and a wild forest populated with trees and worms (columns 28-46).", style_body
    ))
    
    story.append(Paragraph("<b>Interaction Resolvers:</b>", style_h2))
    story.append(Paragraph("• <b>Social Mentoring</b>: When an adult and infant of the same species occupy adjacent cells, "
                           "they initiate mentoring. The infant's brain tensors are updated on the PyTorch device via a linear "
                           "blending interpolation with the adult's weights, accelerating learning.", style_list))
    story.append(Paragraph("• <b>Territorial Combat</b>: Adult males of opposing species that cross paths engage in combat. "
                           "The winner's fitness is boosted, and the loser is removed. If a senior defender blocks a base gate, "
                           "they stall hostile adults, draining the attacker's energy.", style_list))
    story.append(Paragraph("• <b>Agricultural Cultivation</b>: Once a base accumulates 20 mushrooms, 'Agricultural Cultivation' "
                           "unlocks. Adults carrying food can seed nearby garden tiles to cultivate crops, reducing dependency "
                           "on wild forage.", style_list))

    story.append(Paragraph("The weight blending mechanism for mentoring operates directly on GPU/MPS acceleration frameworks:", style_body))
    
    world_mentor_code = """
def mentor_infant(self, adult, infant):
    adult.mentor_cooldown = 15.0
    infant.mentor_cooldown = 15.0

    # Blend neural parameters directly on active PyTorch device (MPS/CPU)
    with torch.no_grad():
        infant.brain.w1 = infant.brain.w1 * 0.85 + adult.brain.w1 * 0.15
        infant.brain.w2 = infant.brain.w2 * 0.85 + adult.brain.w2 * 0.15

    adult.fitness += 1
    adult.thought = f"Teaching {infant.name} how to survive and forage."
    infant.thought = f"Mentored by {adult.name}! Feeling wiser."

    if infant.energy < 40 and adult.food_carried > 0:
        adult.food_carried -= 1
        infant.energy = min(100.0, infant.energy + 40.0)
    """
    story.append(code_block(world_mentor_code))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 6: UI.PY
    # ==========================================
    story.append(Paragraph("Chapter 6: Dynamic Vector Rendering (ui.py)", style_h1))
    story.append(Paragraph(
        "The **SimulationUI** class handles real-time rendering. It draws the active game grid, base enclosures, "
        "and developmental indicators (carried mushrooms, babies, or forest worms). Beyond grid graphics, "
        "the UI features three diagnostic overlays designed for evolutionary monitoring:", style_body
    ))
    
    story.append(Paragraph("<b>1. Neural Brain Synapse Graph</b>", style_h2))
    story.append(Paragraph("A live visualization of the inspected Pac-Man's neural network. It maps the 7 inputs, "
                           "12 hidden nodes, and 6 outputs. Weight lines (synapses) are colored based on charge "
                           "(orange for positive, cyan for negative) with line thickness proportional to connection strength.", style_body))
    
    story.append(Paragraph("<b>2. Population History Plot</b>", style_h2))
    story.append(Paragraph("Plots real-time population sizes of both species over the last 30 intervals, helping engineers "
                           "visualize population booms, competitive exclusions, and extinction events.", style_body))

    story.append(Paragraph("<b>3. System Event Log Overlay</b>", style_h2))
    story.append(Paragraph("Displays a running terminal-style console of global events (births, deaths, theft, invasions, "
                           "eras) at the bottom of the sidebar HUD for instant debugging.", style_body))

    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Closing Notes</b>", style_h1))
    story.append(Paragraph(
        "This architectural setup demonstrates how complex, organic-like behaviors can emerge from simple feedforward "
        "neural inputs when paired with spatial constraints and localized reward mechanics. The modularity of "
        "the decoupled classes ensures that further extensions (like multi-layer brains, deeper cognitive nodes, or "
        "varied map structures) can be integrated without breaking core physics.", style_body
    ))

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)
    print("PDF Generation complete: A_Life_Pacman_Architecture.pdf")

if __name__ == "__main__":
    build_pdf()
