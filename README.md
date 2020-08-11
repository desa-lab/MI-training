# MI-training
Motor imagery brain-computer interface (BCI) systems are a categry of BCIs in which a user self-generates the motor imagery (MI) signal by imagining the movement of different body parts such a hand, a foot or the tongue. The ability of different users is different in generating the MI signals that are classifiable by a computer. This code provides a form of neurofeedback trainin to help users better control their MI signal. 

## How to use 
You need to have the Simulation and Neuroscience Application Platform (SNAP) downloaded and installed from here: https://github.com/sccn/SNAP
SNAP uses Panda3D, so make sure that you have that installed too. 

You also need to have pylsl installed for real-time streaming of the EEG data: https://github.com/labstreaminglayer/liblsl-Python/tree/a13403925ea09361ac2e7e5e66dab2d4681245b0
Feel free to replace this with your method of reading in the EEG data. 

This code uses Scipy and Numpy as well. 

The feedback is provided as the average power on the left and right sides of the motor cortex, that is EEG channels C3, C3, CP3 on the left side and FC4, C4, CP4 on the right side. You can modify this information by modifying the channel locations in `channelLaplaceMatrix` in Line 44 of the code. 


### Citation 
If you use this code, please cite the following paper:

M. Mousavi and V. R. de Sa, "Towards elaborated feedback for training motor imagery brain-computer interfaces," Proceedings of the 7th Graz Brain-Computer Interface Conference 2017, DOI: 10.3217/978-3-85125-533-1-61. 

### Questions/Comments
Please send any questions or comments to mahta@ucsd.edu or mahta.mousavi@gmail.com

Thank you!
