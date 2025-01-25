# Import Vectorworks's built-in 'vs' module
import vs

# Begin the creation of a 3D polygon
vs.BeginPoly3D()

# Define vertex positions
vertex1 = (10.0, 20.0, 5.0)  # X, Y, Z coordinates for the first vertex
vertex2 = (15.0, 25.0, 10.0)  # X, Y, Z coordinates for the second vertex

# Add vertices to the 3D polygon
vs.Add3DPt(vertex1)
vs.Add3DPt(vertex2)

# End the polygon creation
vs.EndPoly3D()