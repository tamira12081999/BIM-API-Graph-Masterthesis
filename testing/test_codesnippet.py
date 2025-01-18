import vs

# Start the 3D polygon creation
vs.BeginPoly3D()

# Add vertices to the polygon
vs.Add3DPt(0, 0, 0)  # First vertex
vs.Add3DPt(100, 0, 0)  # Second vertex
vs.Add3DPt(100, 100, 0)  # Third vertex
vs.Add3DPt(0, 100, 0)  # Fourth vertex

# End the polygon creation
vs.EndPoly3D()