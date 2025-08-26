# Evaluating Keyframe Layouts for Visual Known-Item Search in Homogeneous Collections

This repository contains code for the submission "Evaluating Keyframe Layouts for Visual Known-Item Search in Homogeneous Collections". We publish code for the study application in the folder "application", and publish pre-computed layouts for all (collection, layout) pairs. 

## Setup

Our application is fully Dockerized to enable a reproducible study environment beyond our work. We describe the setup below:

1. Download Docker, e.g., from https://www.docker.com/products/docker-desktop/
2. Run Docker
3. Clone this repository
4. In the command line, change to the "application" folder of this repository
5. Type: docker compose up --build
6. The application is now served at: http://localhost:5173/
7. All data produced is stored in backend/CollectedData, including scroll data, target overlays, and submissions

## Pre-Computed Grids

We furthermore provide pre-computed grids in the "grids" folder. In total, we employed 35 collections and 7 layouts, leading to 245 (collection,layout) pairs. For reproducibility, we share the exact arrangement of images on the grid. We share the .txt files necessary to reproduce the grids and provide .png thumbnails of the grids.


 
