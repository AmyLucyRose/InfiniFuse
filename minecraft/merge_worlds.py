from .dimension import Dimension
from .mcafile import McaFile
from .world import World
import datetime
import os

# Find offset for map
# Offset all chunks
# Change map IDs
# Offset map items
# Offset players
# Combine player stats
# Do something with player inventory ?

def point(x : int = 0, z : int = 0):
    return {'x' : x, 'z' : z}

def rectangle( minimum : point = None, maximum : point = None):
    minimum = minimum or point(0, 0)
    maximum = maximum or point(0, 0)
    return {'min' : minimum, 'max' : maximum}

def dimension_binary_map(dimension : Dimension):
    """Map all chunks from <dimension> to a two dimensional array of booleans"""
    print(f'[{datetime.datetime.now()}] Making binary map')
    x = []
    z = []
    maps = {}
    
    for fileName in os.listdir(dimension.folder):
        if os.path.splitext(fileName)[1] == '.mca':
            f = McaFile(os.path.join(dimension.folder, fileName))
            xRegion, zRegion = f.coords_region
            xChunk, zChunk = f.coords_chunk
            x += [xChunk, xChunk + 31]
            z += [zChunk, zChunk + 31]
            maps[xRegion, zRegion] = f.binary_map()
    
    print(f'[{datetime.datetime.now()}] Done !')
    data = {
        'map' : maps,
        'pos' : rectangle(
            minimum = point(min(x), min(z)),
            maximum = point(max(x), max(z))
        )
    }
    return data

def generate_offsets(maxRadius : int = 3_750_000):
    """Generate x and z coordinates in concentric squares around the origin"""
    for radius in range(maxRadius):
        for x in range(-radius, radius + 1):
            if abs(x) == abs(radius):
            # Top and bottom of the square
                for z in range(-radius, radius + 1):    
                    yield {'x' : x, 'z' : z}
            else:
            # Sides of the square
                yield {'x' : x, 'z' : -radius}
                yield {'x' : x, 'z' :  radius}

def fuse(base : World, other : World):
    """Fuse two maps into one. Takes a REALLY long time ! (Could be days)"""
    
    a = dimension_binary_map(base.dimensions['minecraft:overworld'])
    # Binary map of <base>'s overworld
    
    b = dimension_binary_map(other.dimensions['minecraft:overworld'])
    # Binary map of <other>'s overworld
    
    sidelen = McaFile.sideLength
    # Side length of a region file in chunks
    
    defaultSearch = {'min' : 0, 'max' : sidelen - 1}
    # Default search area limits inside a region file

    # Initialize all points and rectangles at once, outside of the loop


    b['new'] = rectangle() # New coordinates of b after offset
    
    o = {} # Overlap region of A and B
    o['pos'] = rectangle() # Overlap absolute chunk coords
    o['reg'] = rectangle() # Overlap region coords
    o['cnk'] = rectangle() # Overlap region-relative chunk coords
    
    search = rectangle() # Search area inside region file
    
    regionPos = point() # Chunk coords of region currently checked for overlap
    
    chunk = {} # Coordinates of chunk currently checked for overlap
    chunk['pos'] = point() # Chunk absolute chunk coords
    chunk['reg'] = point() # Chunk region coords
    chunk['cnk'] = point() # Chunk region-relative chunk coords
    
    
    print(f'[{datetime.datetime.now()}] Trying offsets...')
    for offset in generate_offsets():
        # Some random numbers just to test the math, comment out when not needed
        #offset = {'x' : 53, 'z' : 7}
        
        for p in b['pos']:
            for i in b['pos'][p]:
            
                # Offset new coordinates of b
                b['new'][p][i] = b['pos'][p][i] + offset[i]
                
                # Find absolute position of overlap
                o['pos'][p][i] = min(max(b['new'][p][i], a['pos']['min'][i]), a['pos']['max'][i])
                
                # Convert overlap position to region and chunk
                o['reg'][p][i], o['cnk'][p][i] = divmod(o['pos'][p][i], sidelen)
        
        # Check all chunks inside the overlapping area
        conflict = False
        for coords, region in a['map'].items():
            regionPos['x'] = coords[0]
            regionPos['z'] = coords[1]
            
            for i in regionPos:
                if regionPos[i] not in range(o['reg']['min'][i], o['reg']['max'][i] + 1):
                    break
                
            else:
            
                # If region is on the edge of the overlap, serach only relevant chunks
                for p in search:
                    for i in search[p]:
                        if regionPos[i] == o['reg'][p][i]:
                            search[p][i] = o['cnk'][p][i]
                        else:
                            search[p][i] = defaultSearch[p]
                
                for x, row in enumerate(region[search['min']['x'] : search['max']['x'] + 1]):
                    for z, chunkExists in enumerate(region[x][search['min']['z'] : search['max']['z'] + 1]):
                        if chunkExists:
                            
                            chunk['pos']['x'] = x
                            chunk['pos']['z'] = z
                            
                            for i in chunk['pos']:
                                
                                # Convert from search-relative to a-relative
                                chunk['pos'][i] += search['min'][i] + regionPos[i] * sidelen
                                
                                # Convert from a-relative to b-relative
                                chunk['pos'][i] -= offset[i]
                                
                                # Convert to region and chunk
                                chunk['reg'][i], chunk['cnk'][i] = divmod(chunk['pos'][i], sidelen)
                            
                            regionIdx = (chunk['reg']['x'], chunk['reg']['z'])
                            if regionIdx in b['map']:
                                conflict = b['map'][regionIdx][chunk['cnk']['x']][chunk['cnk']['z']]
                        if conflict:
                            break
                    if conflict:
                        break
                if conflict:
                    break
        else:
            print(f'[{datetime.datetime.now()}] No conflict with offset {offset}')
            break
        
                
        '''for x, row in enumerate(region[search['x']['min'] : search['x']['max'] + 1]):
                    for z, chunkExists in enumerate(region[x][search['z']['min'] : search['z']['max'] + 1]):
                        if chunkExists:
                            #print(f'Checking chunk {x} {z}')
                        
                            # Calculate real coordinates of x and z
                            realX = x + search['x']['min'] + xRegion * McaFile.sideLength
                            realZ = z + search['z']['min'] + zRegion * McaFile.sideLength
                            
                            # Offset relative to B
                            # (B is positively offset from to A, so A is negatively offset from B)
                            bX = realX - offset['x']
                            bZ = realZ - offset['z']
                            
                            # Convert to region and chunk coordinates
                            bxRegion, bxChunk = divmod(bX, McaFile.sideLength)
                            bzRegion, bzChunk = divmod(bZ, McaFile.sideLength)
                            
                            if (bxRegion, bzRegion) in b['map']:
                                if b['map'][bxRegion, bzRegion][bxChunk][bzChunk] is True:
                                    conflict = True
                        if conflict:
                            break
                    if conflict:
                        break
            if conflict:
                break
        else:
            print(f'[{datetime.datetime.now()}] No conflict with offset {offset}')
            return'''

'''{'xMin': -256, 'zMin': -320, 'xLen': 512, 'zLen': 864}'''