---
title: 'CoperniFUS: A flexible Python-based GUI for stereotaxic Focused UltraSound (FUS) experiment planning'
tags:
  - Python
  - Experimental Neuroscience
  - Ultrasound neurostimulation
authors:
  - name: Tom Aubier
    orcid: 0009-0004-5558-8435
    affiliation: 1 # (Multiple affiliations must be quoted)
    corresponding: true # (This is how to denote the corresponding author)
  - name: Sandrine Parrot
    affiliation: 2
  - name: Ivan M. Suarez-Castellanos
    affiliation: 1
  - name: W. Apoutou N'Djin
    affiliation: 1
affiliations:
 - name: LabTAU, INSERM, Centre Léon Bérard, Université Claude Bernard Lyon 1, F-69003, Lyon, France
   index: 1
 - name: Université Claude Bernard Lyon 1, INSERM, Centre de Recherche en Neurosciences de Lyon CRNL U1028 UMR5292, F-69500 Bron, France
   index: 2
date: 7 February 2025
bibliography: neustim.bib

# Optional fields if submitting to a AAS journal too, see this blog post:
# https://blog.joss.theoj.org/2018/12/a-new-collaboration-with-aas-publishing
# aas-doi: 10.3847/xxxxx <- update this with the DOI from AAS once you know it.
# aas-journal: Astrophysical Journal <- The name of the AAS journal.
---

# Summary

Focused UltraSound (FUS) is gaining increasing interest for its potential as a minimally-invasive yet targeted alternative to existing neurostimulation modalities.
Although reversible changes in the activity of neural structures have been reported as far back as 1929 [@Harvey1929], comprehensive descriptions of the short- and long-term effects of ultrasound on neural structures are still lacking to achieve neurostimulation with satisfactory levels of control and safety. Delivering well characterized FUS pulses with a high degree of spatial selectivity along with local assessment of the state and activity of specific brain regions is crucial in pursuing this research.
Unlike most electrophysiology procedures involving compact needle-like probes that can be achieved using stereotaxic frame limited to three degrees of freedom, FUS experiments on small _in vivo_ models often require the implementation of complex probe layouts to assess the activity of the stimulated neural structures.
Treatment planning, evaluation of acoustic parameters through simulations, and post-processing of results often rely on distinct softwares with their own coordinate systems which greatly complicates the integration, analysis and interpretation of key information, thus limiting the ability to properly describe the spatiotemporal aspects of FUS neurostimulation dynamics.

`CoperniFUS` aims to overcome this obstacle by providing a flexible software platform to plan FUS procedures using stereotaxic frames thanks to a unified coordinate system architecture. Moreover `CoperniFUS` provides the possibility to take anatomical variability into consideration by including the registration of anatomical landmark.

# Statement of need

<!-- // Relevance of studies on FUS-induces microenvironment alteration -->
In an effort to assess the therapeutic potential of ultrasound neurostimulation, studies have sought  to characterize the effect of ultrasound on the biochemical micro-environment of brain structures after stimulations. While tools like Magnetic Resonance Spectroscopy (MRS) offer a non-invasive way of assessing the concentrations of metabolites _in vivo_, they come with significant limitations. Concentration measurements are non-specific, only representative of the total metabolic, extra- and intra-cellular quantity of a compound [@Dyke2017]. The spatial selectivity of the method is also limited to minimum voxel volumes of several cm<sup>3</sup>. Finally, the difficulties arising from the integration of FUS transducers in MRIs are preventing the further investigation of _online_ effects [@Yaakub2023].

<!-- // FUS targetting -->
Studies on rodent models have been pursued using invasive methods such as microdialysis [@Min2011; @Yang2012]. Although these studies report effects of FUS stimulations on Dopamine, Serotonin or GABA levels, their observations are restricted to low ultrasound central frequencies resulting in poorly spatially-selective stimulation, which complicates the assessment of region-specific responses. Despite the interest in characterizing spatially selective stimulations to characterize any region-dependence [@Suarez-Castellanos2021; @Murphy2024a], the choice of low frequencies is typically made to maximize energy transfer through the skull and minimize pressure field distortions. Transducer placement and targeting of the structure is empirical, based on trigonometric evaluation of the focus relative to reference atlases.

<!-- // acoustic simulations -->
With the growing interest in transcranial ultrasound therapeutic approaches, extensive research has been conducted to develop and validate computational models of acoustic wave propagation through the skull. Although a number of tools and formalisms exist [@Aubry2022a; @Murphy2025], k-Wave [@Treeby2010] has been widely adopted in the field of ultrasound neurostimulation specifically [@Constans2018; @Verhagen2019; @Yaakub2023]. Acoustic simulations in this context are performed using standalone Matlab scripts for the definition of acoustic sources and domains. Acoustic domains are defined either directly based on CT or pseudo-CT scans [@Aubry2003], or by constructing maps from rasterized brain and skull meshes. Registration of the transducer location relative to targeted brain structures is often achieved using frameless optical tracking neuronavigation systems on human or non-human primate subjects [@Murphy2025]. However, empirical methods are usually chosen in small rodents experiments due to the space constraints associated with these models.

<!-- // structure atlases + morpho calib -->
Targeting of brain structures is achieved using reference atlases registered to MRI scans of subjects when available. However for small animals, these images are typically not acquired in a systematic way. Targeted structures coordinates are thus directly evaluated on reference atlases, based on an anatomical landmark such as the Bregma skull suture on rats and mice [@Kleven2023; @Wang2020]. Morphological variability between subjects can compromise experiments if it is not taken into account, however registration of reference atlases to anatomical measurements can be tedious and is rarely reported in rodent studies.

# Features

In this context we developed `CoperniFUS`, a modular software tool offering a common coordinate manipulation platform specifically suited for stereotaxic experiments. Currently available modules allow the manipulation of brain atlases, meshes. They also enable _in situ_ k-Wave acoustic simulations, with the aim of facilitating the coupling of FUS neurostimulation setups with standard electrophysiology methods such as microdialysis [@Min2011], fiber photometry [@Murphy2024a] or fast-scan cyclic voltametry [@Olaitan2024]. With the emergence of Python as the programming language of choice in neuroscience [@Muller2015], we chose to design a Python tool that can be easily tweaked and augmented with specialized modules to fit a large range of research needs involving stereotaxic frame-based experiments.

![Overview of `CoperniFUS`'s graphical interface structure.\label{fig:example}](figures/CoperniFUS_ui_breakdown.png)

As of the writing of this article, `CoperniFUS` currently enables:
1. Facilitated stereotaxic targeting of specific brain structures for a large range of species thanks to the integration of the `BrainGlobe API` [@Claudi2020a].
2. Arbitrary stereotaxic frames can be constructed using a flexible dictionary-based editor. Discrete stereotaxic frame elements (referred as `Armatures`) can be associated in a hierarchical tree structure, allowing operations such as mesh boolean operations or acoustic simulations to be performed in any coordinate reference frame.
3. In the absence of whole head CT or MRI scans that allow for accurate atlas registration, `CoperniFUS` provides a mean of minimizing the targeting errors that can arise from anatomical variability. To that end, 3D objects such as atlases or skull meshes can inherit from an anatomically calibrated coordinate frame whose scale and orientation can be easily matched to subjects using anatomical landmarks such as Lambda and Bregma for rodents.
4. Skull meshes can be loaded to aid probe implantation planning and be accounted in k-Wave acoustic simulations. Craniotomies can also be simulated with support for boolean operation. More generally, a broad variety of mesh operations can be achieved thanks to the integration of the Python library `trimesh` [@Dawson-Haggerty2019].
5. Axisymmetric simulations in homogeneous domains and 3D simulations in complex mediums derived from mesh objects can be conducted in built-in Armatures. This integration alleviates the need to redefine sources and domains in external softwares. Quantitative assessment of the targeting of FUS stimulations can be performed programmatically by evaluating for example the intersection of the simulated FUS focal spot with a specific brain structure.

# Software architecture

The software is composed of a viewer graphical interface based on `PyQt6`, hosting a `pyqtgraph` 3D viewport. Modules are integrated to the GUI as dockable elements and allow the manipulation of objects that can be visualized in the viewport. At its core, `CoperniFUS` is equipped with three built-in modules: *1.* the `Tooltip module`, which allows the user to input coordinates, visualized in the viewer by an axis triad. Section views of items displayed in the viewport can be performed along planes normal to its $x$, $y$ and $z$ axes. Furthermore, Tooltip coordinates can be referenced by any modules, facilitating anatomical landmark registration, or assessment of distances / locations in any coordinate frames. *2.* The `Stereotaxic frame module` handles the creation of arbitrary stereotaxic frames using `armatures` objects that can be combined in a hierarchical structure. At its core, an `armature` consists of a series of affine transformation operations (translation & rotation) that allows the modeling rigid frames. Specialized armature objects also exist to perform operations in the coordinates of stereotaxic frame elements. Thus, `trimesh armatures` have been developed to perform import `.stl` meshes, create arbitrary geometries programmatically or perform operations such as booleans or `convexhull` mesh generation. A dedicated armature object leveraging the Python implementation of k-Wave [@Yagubbbayli2024] has been designed to evaluate pressure field in the context of FUS neurostimulation studies. From a programmer perspective, specialized armatures inherit from a common `Armature` class, which implements the coordinate transformation logic and user interface aspects. *3.* Finally, the `Anatomical registration helper` module handles spatial transformations required to match the location, rotation and scale of atlases and objects such as skull meshes or reference images to anatomical landmarks acquired experimentally. As represented on \autoref{hierarchical_coordinate_system}, coordinate frame associated to modules and armatures used throughout the software are part of a common hierarchical system. Any objects displayed in the viewer can thus be easily set to inherit from the anatomically calibrated coordinate system.

![Illustration of `CoperniFUS`'s hierarchical coordinate system in the context of a study involving ultrasound neurostimulation coupled to microdialysis sampling. From the users perspective, this  hierarchical structure of armatures can be established and edited graphically through _drag and drop_ of armatures shown in the tree view of the stereotaxic module. Inheritance to the anatomically calibrated coordinate frame can be disabled for specific objects by setting `ignore_anatomical_landmarks_calibration` to `True` in its associated configuration dictionary.\label{hierarchical_coordinate_system}](figures/hierarchical_coordinate_system.jpg){width=80%}

Optional modules are also available to add brain atlases to the viewport available via the `BrainGlobe` API (`Brain Atlas module`), reference images can also be imported (`Images as planes modules`) as well as `stl` meshes (`STL handler module`).

Application states are continuously stored in a user readable dictionary-like `json` file. Multiple configuration files can be created switched between, allowing the user to save stereotaxic frame configurations and atlas anatomical registrations corresponding to specific subjects for post processing of experiments results. Configuration dictionaries for armature objects can additionally be modified in a build in text editor. Variables contained in this dictionary can be made editable from the GUI itself, in a dedicated section of the stereotaxic frame module dock.

Finally, data analysis and manipulation can be greatly simplified by using `CoperniFUS` in interactive mode. The application can indeed be started as a standalone software from a terminal, or can be used dynamically in a [Jupyter notebook](https://jupyter.org). In this mode, data manipulated in the viewer, modules and armatures can be programmatically grabbed and processed using python.

# Acknowledgements

This project was supported by the French National Research Agency (ANR-16-TERC0017, ANR-21-CE19-0007 \& ANR-21-CE19-0030), the American Focused Ultrasound Foundation (LabTAU, FUSF Center of Excellence). Additionally, this work was performed within the framework of the LABEX DEV WECAN (ANR-10-LABX-0061) and CORTEX (ANR-11-LABX-0042) of Université de Lyon, within the program "Investissements d'Avenir" (ANR-11-IDEX-0007) operated by the French National Research Agency (ANR). The work of the communities behind k-Wave and the Python packages used throughout this work was integral to its completion.

# References