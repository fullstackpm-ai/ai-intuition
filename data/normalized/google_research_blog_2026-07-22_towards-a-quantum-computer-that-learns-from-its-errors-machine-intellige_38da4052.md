---
id: google_research_blog_2026-07-22_towards-a-quantum-computer-that-learns-from-its-errors-machine-intellige_38da4052
lane: frontier_primitives
published_at: '2026-07-22T00:00:00+00:00'
raw_artifact_id: google_research_blog_2026-07-22_towards-a-quantum-computer-that-learns-from-its-errors-machine-intellige_38da4052
source_id: google_research_blog
title: Towards a quantum computer that learns from its errors Machine Intelligence
  · Quantum
url: https://research.google/blog/towards-a-quantum-computer-that-learns-from-its-errors/
---

# Towards a quantum computer that learns from its errors

Towards a quantum computer that learns from its errors

July 22, 2026

Volodymyr Sivak and Paul Klimov, Research Scientists, Google Quantum AI, Google Research

By integrating reinforcement learning with quantum error correction, we showed that a quantum computer can continuously adapt to drift and remain stable during long computations.

Quick links

Paper

Share Copy link ×

Copy link ×

Imagine a symphony orchestra performing a complex masterpiece. If the violins drifted out of tune every few measures, the ensemble would constantly have to stop and retune their instruments. Thankfully, this doesn't happen in an orchestra because the instruments reliably stay in tune. However, it is the current reality of operating a quantum computer.

Since quantum computers are fundamentally analog machines that are sensitive to drift, maintaining reliable operation requires perpetually recalibrating their control parameters, i.e., the frequencies, amplitudes, and phases of the analog signals choreographing the qubits. Today, this requires fully terminating the entire quantum computation. This complete decoupling of computation and calibration represents a fundamental bottleneck for the future, as useful quantum algorithms must run continuously for days or even months.

To address this, in “ Reinforcement learning control of quantum error correction ”, published in Nature , we demonstrated a reinforcement learning (RL) framework in which an autonomous agent learns from quantum error detections to continuously steer thousands of control parameters, stabilizing the quantum system against drift during the computation. In short: we found a way to tune the instruments while the music plays.

Dealing with quantum errors

In a concert hall, a detuned instrument is immediately heard. The quantum realm offers no such luxury. As if the very act of listening ruined the performance, measuring the qubits collapses their quantum superposition states. To preserve the quantum information, we instead employ Quantum Error Correction (QEC), a technique that exploits redundancy to create “logical qubits” out of many physical qubits, and uses specialized parity checks on the physical qubits to digitize the analog noise into binary error detection events.

Unfortunately, these bits only tell us that an error occurred somewhere within a bounded spacetime region of the quantum circuit, not its exact location. It is like hearing a sour note without knowing exactly which musician played it. To pinpoint the likely error locations and calculate the necessary corrections, we rely on QEC decoders, such as the neural network decoder AlphaQubit (trained on real data) and algorithmic decoder Tesseract . If errors are sufficiently rare, these decoders can successfully restore the logical quantum information by analyzing the error detection data. However, decoders leave a crucial question unanswered: why did those errors happen in the first place?

Some errors result from the unavoidable interaction of a quantum system with its surrounding environment, leading to decoherence . This ruthless process destroys macroscopic quantum superpositions, effectively turning quantum computers into classical ones. This fundamental phenomenon is so pervasive that it causes our familiar classical reality to emerge from the underlying quantum laws of Nature. While these environmental errors can never be completely prevented, many others are manifestations of imprecise control calibration and hardware drift – flaws that remain within our power to mitigate.

Beyond traditional physics models

Traditionally, quantum calibration relied on physics models. Its techniques were refined through decades of quantum control research. However, across technological domains, human-crafted models inevitably hit a performance ceiling. Early computer vision stalled when relying on strict geometric rules. Traditional robotics still struggles with kinematic equations that fail to capture the messy reality of contact dynamics and friction. Similarly, the decades-old challenge of predicting protein folding remained largely intractable for traditional physical models until deep learning systems like AlphaFold achieved unprecedented accuracy. Across these fields, new breakthroughs occurred when the approach shifted toward learning directly from data.

Recently, AlphaQubit surpassed the accuracy of the most powerful algorithmic QEC decoders. Now quantum control faces the same ceiling. As quantum processors improve through progress in fabrication and hardware, their errors become dominated by complex phenomena that are challenging for traditional modeling and calibration. Can machine learning bring new advances?

Don’t just correct errors, learn from them!

Google Research has a rich history of pioneering RL to solve problems too complex for traditional programming. Unlike algorithms relying on explicit instructions, RL operates through experience. An autonomous agent tests different behaviors and learns directly from resulting errors to refine its strategy. Applying RL to achieve accurate, continuous quantum calibration felt almost inevitable. Since QEC already generates a steady stream of detection events, we simply granted this data a complementary role. In addition to decoding it and correcting the errors, we employ the detection events as an active learning signal. As computation progresses, the RL agent monitors this data and learns to dynamically steer the control parameters, counteracting drift and preventing new errors.

Quantum computation is physically realized via analog control signals. The quantum error detection events are used by the decoder to infer logical corrections. In our control framework, they are also repurposed as a learning signal, teaching the RL agent to continuously steer thousands of control parameters and stabilize the quantum system during the computation.

Our quantum control experiment

We validated such RL quantum control on our flagship Willow superconducting processor. By deliberately injecting artificial drift of control parameters, we showed that RL steering improved the logical stability of our error-correcting code 3.5-fold, prolonging the time during which the processor acts as a reliable “quantum memory” device.

Typically, tuning the processor to peak performance relied heavily on a “human-in-the-loop” approach, with scientists applying physical intuition to resolve edge cases that are difficult to automate. Yet, even after this exhaustive expert calibration, subsequent RL fine-tuning systematically suppressed the logical error rate by an additional 20%.

The synthesis of all our technologies in this experiment reduced the logical errors in quantum memories to a record low: fewer than one per thousand error correction cycles in the surface code , and one per hundred in the color code .

QEC prolongs the lifetime of logical information in quantum memories based on the surface code ( left ) and color code ( right ). RL fine-tuning of our controller improves the quality of QEC by circumventing the limitations of complex physics models and human intuition.

Does it scale?

A critical question from machine learning and quantum researchers is whether this RL approach can scale to large quantum computers of the future. To test this, we conducted numerical simulations with hundreds of qubits and tens of thousands of control parameters.

In our simulation, a miscalibrated system starts at a high physical error rate. The agent steadily reduces it over time by learning improved control parameters, and thanks to QEC the logical error rate (LER) gets suppressed exponentially in system size (i.e. number of physical qubits). Crucially, the speed at which physical error rate is reduced by RL is independent of this size, which allows us to scale this approach to much larger systems.

The simulations confirmed our expectation: the number of required RL training iterations (epochs) is independent of the system size, owing to the local sensitivity of the QEC detection events to errors. However, realizing the full potential of the RL framework requires tighter integration. By speeding up the communication cycle between the agent and the quantum processor, and employing more advanced machine learning methods, we hope to unlock significant additional improvements.

Our work thus enables a new paradigm: a quantum computer that learns from its errors and doesn’t stop computing.

Acknowledgements

We thank our co-authors for their contributions, including building and maintaining the hardware, software, cryogenics and electronics infrastructure. This work was made possible by the Google Quantum AI team at Google Research, in collaboration with teams from Google DeepMind.

Labels:

Machine Intelligence

Quantum

Quick links

Paper

Share Copy link ×

Copy link ×

Other posts of interest

July 15, 2026 Towards demystifying the creativity of diffusion models Algorithms & Theory · Generative AI · Machine Intelligence

July 15, 2026

Algorithms & Theory ·

Generative AI ·

Machine Intelligence

July 9, 2026 SensorFM: Towards a general intelligence and interface for wearable health data Generative AI · Machine Intelligence

July 9, 2026

Generative AI ·

Machine Intelligence

June 30, 2026 Introducing TabFM: A zero-shot foundation model for tabular data Data Management · Machine Intelligence · Product

June 30, 2026

Data Management ·

Machine Intelligence ·

Product