"""Verification script to check Qiskit and Qiskit Aer simulation environment."""

import qiskit
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

def verify_bell_state():
    print("Qiskit version:", qiskit.__version__)
    
    # Create a Quantum Circuit acting on 2 qubits
    circuit = QuantumCircuit(2, 2)
    
    # Add a Hadamard gate on qubit 0 to create superposition
    circuit.h(0)
    # Add a CNOT gate on control qubit 0 and target qubit 1 to entangle them
    circuit.cx(0, 1)
    
    # Map the quantum measurement to the classical bits
    circuit.measure([0, 1], [0, 1])
    
    # Initialize the Aer Simulator
    simulator = AerSimulator()
    
    # Execute the circuit on the simulator
    print("Running simulator...")
    job = simulator.run(circuit, shots=1000)
    result = job.result()
    
    # Get the count of measurement results
    counts = result.get_counts(circuit)
    print("Measurement counts (should show ~500 for '00' and ~500 for '11'):")
    print(counts)
    
    # Basic check to make sure both states were observed
    assert '00' in counts and '11' in counts, "Bell state verification failed!"
    print("Verification SUCCESS!")

if __name__ == "__main__":
    verify_bell_state()
