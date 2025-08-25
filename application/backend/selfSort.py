#This code is mostly based on code from: https://github.com/Visual-Computing/LAS_FLAS/

#!/usr/bin/env python3

import time, lap
import numpy as np
from scipy.ndimage import uniform_filter1d, convolve1d


''' Calculates the squared L2 (eucldean) distance using numpy. '''
def squared_l2_distance(q, p):
    
    ps = np.sum(p*p, axis=-1, keepdims=True)    
    qs = np.sum(q*q, axis=-1, keepdims=True)
    distance = ps - 2*np.matmul(p, q.T) + qs.T
    return np.clip(distance, 0, np.inf)

''' Applies a low pass filter to the current map'''
def low_pass_filter(map_image, filter_size_x, filter_size_y, wrap=False):
    
    mode = "wrap" if wrap else "reflect" # nearest
    
    im2 = uniform_filter1d(map_image, filter_size_y, axis=0, mode=mode)  
    im2 = uniform_filter1d(im2, filter_size_x, axis=1, mode=mode)  
    return im2

''' Utility function that takes a position and returns 
a desired number of positions in the given radius'''
def get_positions_in_radius(pos, indices, r, nc, wrap):
    if wrap:
        return get_positions_in_radius_wrapped(pos, indices, r, nc)
    else:
        return get_positions_in_radius_non_wrapped(pos, indices, r, nc)
    
''' Utility function that takes a position and returns 
a desired number of positions in the given radius'''
def get_positions_in_radius_non_wrapped(pos, indices, r, nc):
    
    H, W = indices.shape
    
    x = pos % W 
    y = int(pos/W)
    
    ys = y-r
    ye = y+r+1
    xs = x-r
    xe = x+r+1
    
    # move position so the full radius is inside the images bounds
    if ys < 0:
        ys = 0
        ye = min(2*r + 1, H)
        
    if ye > H:
        ye = H
        ys = max(H - 2*r - 1, 0)
        
    if xs < 0:
        xs = 0
        xe = min(2*r + 1, W)
        
    if xe > W:
        xe = W
        xs = max(W - 2*r - 1, 0)
    
    # concatenate the chosen position to a 1D array
    positions = np.concatenate(indices[ys:ye, xs:xe])
    
    if nc is None:
        return positions
    
    chosen_positions = np.random.choice(positions, min(nc, len(positions)), replace=False)
    
    return chosen_positions

''' Utility function that takes a position and returns 
a desired number of positions in the given radius'''
def get_positions_in_radius_wrapped(pos, extended_grid, r, nc):
    
    H, W = extended_grid.shape
    
    # extended grid shape is H*2, W*2
    H, W = int(H/2), int(W/2)    
    x = pos % W 
    y = int(pos/W)
    
    ys = (y-r + H) % H     
    ye = ys + 2*r + 1 
    xs = (x-r + W) % W 
    xe = xs + 2*r + 1 
    
    # concatenate the chosen position to a 1D array
    positions = np.concatenate(extended_grid[ys:ye, xs:xe])
    
    if nc is None:
        return positions
    
    chosen_positions = np.random.choice(positions, min(nc, len(positions)), replace=False)
    
    return chosen_positions

# Fast Linear Assignment Sorting
def sort_with_flas(X, filepaths, nc, n_images_per_site, radius_factor=0.9, wrap=False, return_time=False):
    
    np.random.seed(7)   # for reproducible sortings
    
    # setup of required variables
    N = np.prod(X.shape[:-1])       # number of images (in X)
    X = X.reshape((len(X) // n_images_per_site, n_images_per_site, -1))
    filepaths = np.array(filepaths)
    grid_shape = X.shape[:-1]
    H, W = grid_shape
    
    start_time = time.time()
    
    # assign input vectors to random positions on the grid
    grid = np.random.permutation(X.reshape((N, -1))).reshape((X.shape)).astype(float)
    
    # reshape 2D grid to 1D
    flat_X = X.reshape((N, -1))
    
    # create indices array 
    indices = np.arange(N).reshape(grid_shape)
    
    if wrap:
        # create a extended grid of size (H*2, W*2)
        indices = np.concatenate((indices, indices), axis=1 )
        indices = np.concatenate((indices, indices), axis=0 )
    
    radius_f = max(H, W)/2 - 1 # initial radius
        
    while True:
        # compute filtersize that is smaller than any side of the grid
        radius = int(radius_f)
        filter_size_x = min(W-1, int(2*radius + 1))
        filter_size_y = min(H-1, int(2*radius + 1))
        
        # Filter the map vectors using the actual filter radius
        grid = low_pass_filter(grid, filter_size_x, filter_size_y, wrap=wrap)
        flat_grid = grid.reshape((N, -1))
        
        n_iters = 2 * int(N / nc) + 1
        max_swap_radius = int(round(max(radius, (np.sqrt(nc)-1)/2)))
            
        for i in range(n_iters):
            
            # find random swap candicates in radius of a random position
            random_pos = np.random.choice(N, size=1)
            positions = get_positions_in_radius(random_pos[0], indices, max_swap_radius, nc, wrap=wrap)
            
            # calc C
            pixels = flat_X[positions]
            grid_vecs = flat_grid[positions]
            C = squared_l2_distance(pixels, grid_vecs)
            
            # quantization of distances speeds up assingment solver
            C = (C / C.max() * 2048).astype(int)
            
            # get indices of best assignments 
            _, best_perm_indices, _= lap.lapjv(C)
            
            # assign the input vectors to their new map positions
            flat_X[positions] = pixels[best_perm_indices]
            filepaths[positions] = filepaths[positions][best_perm_indices]
        
         # prepare variables for next iteration
        grid = flat_X.reshape(X.shape)
        
        radius_f *= radius_factor
        # break condition
        if radius_f < 1:
            break
               
    duration = time.time() - start_time
    
    if return_time:
        return grid, filepaths, duration
    
    print(f"Sorted with FLAS in {duration:.3f} seconds") 
    return grid, filepaths