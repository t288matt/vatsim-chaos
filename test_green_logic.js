// Test the green aircraft logic
const allFlights = [
    "FLT0001", "FLT0002", "FLT0003", "FLT0004", "FLT0005", "FLT0006", "FLT0007", "FLT0008", "FLT0009", "FLT0010",
    "FLT0011", "FLT0012", "FLT0013", "FLT0014", "FLT0015", "FLT0016", "FLT0017", "FLT0018", "FLT0019", "FLT0020",
    "FLT0021", "FLT0022", "FLT0023", "FLT0024", "FLT0025", "FLT0026", "FLT0027", "FLT0028", "FLT0029", "FLT0030",
    "FLT0031", "FLT0032", "FLT0033", "FLT0034", "FLT0035", "FLT0036", "FLT0037", "FLT0038", "FLT0039", "FLT0040"
];

// Flights with conflicts (from our analysis)
const conflictFlights = new Set([
    "FLT0001", "FLT0002", "FLT0003", "FLT0004", "FLT0005", "FLT0007", "FLT0008", "FLT0009", "FLT0010",
    "FLT0013", "FLT0014", "FLT0015", "FLT0016", "FLT0017", "FLT0018", "FLT0019", "FLT0020", "FLT0021",
    "FLT0022", "FLT0023", "FLT0024", "FLT0025", "FLT0027", "FLT0030", "FLT0032", "FLT0033", "FLT0034",
    "FLT0035", "FLT0036", "FLT0037", "FLT0038", "FLT0039"
]);

// Find green flights
const greenFlights = allFlights.filter(flight => !conflictFlights.has(flight));

console.log("Total flights:", allFlights.length);
console.log("Flights with conflicts:", conflictFlights.size);
console.log("Flights that should be green:", greenFlights.length);
console.log("Green flights:", greenFlights);

// Test the logic from the animation
const flightsWithConflicts = new Set();
// Simulate the conflicts array
const conflicts = [
    { flight1: "FLT0001", flight2: "FLT0002" },
    { flight1: "FLT0003", flight2: "FLT0009" },
    // ... more conflicts
];

conflicts.forEach(conflict => {
    flightsWithConflicts.add(conflict.flight1);
    flightsWithConflicts.add(conflict.flight2);
});

console.log("\nAnimation logic test:");
console.log("Flights with conflicts (from animation logic):", flightsWithConflicts.size);

// Test which flights would be green
const animationGreenFlights = allFlights.filter(flight => !flightsWithConflicts.has(flight));
console.log("Flights that would be green (animation logic):", animationGreenFlights.length);
console.log("Animation green flights:", animationGreenFlights); 