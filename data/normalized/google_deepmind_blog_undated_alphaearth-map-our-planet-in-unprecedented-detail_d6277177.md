---
id: google_deepmind_blog_undated_alphaearth-map-our-planet-in-unprecedented-detail_d6277177
lane: frontier_primitives
published_at: null
raw_artifact_id: google_deepmind_blog_undated_alphaearth-map-our-planet-in-unprecedented-detail_d6277177
raw_path: data/raw/lab-posts/google_deepmind_blog_undated_alphaearth-map-our-planet-in-unprecedented-detail_d6277177.html
source_id: google_deepmind_blog
source_name: Google DeepMind Blog
source_type: html
title: AlphaEarth Map our planet in unprecedented detail
url: https://deepmind.google/blog/alphaearth-foundations-helps-map-our-planet-in-unprecedented-detail/
---

# AlphaEarth Foundations helps map our planet in unprecedented detail — Google DeepMind

AlphaEarth Foundations helps map our planet in unprecedented detail

The AlphaEarth Foundations team

New AI model integrates petabytes of Earth observation data to generate a unified data representation that revolutionizes global mapping and monitoring

Every day, satellites capture information-rich images and measurements, providing scientists and experts with a nearly real-time view of our planet. While this data has been incredibly impactful, its complexity, multimodality and refresh rate creates a new challenge: connecting disparate datasets and making use of them all effectively.

Today, we’re introducing AlphaEarth Foundations, an artificial intelligence (AI) model that functions like a virtual satellite. It accurately and efficiently characterizes the planet’s entire terrestrial land and coastal waters by integrating huge amounts of Earth observation data into a unified digital representation, or " embedding, " that computer systems can easily process. This allows the model to provide scientists with a more complete and consistent picture of our planet's evolution, helping them make more informed decisions on critical issues like food security, deforestation, urban expansion, and water resources.

To accelerate research and unlock use cases, we are now releasing a collection of AlphaEarth Foundations’ annual embeddings as the Satellite Embedding dataset in Google Earth Engine . Over the past year, we’ve been working with more than 50 organizations to test this dataset on their real-world applications.

Our partners are already seeing significant benefits, using the data to better classify unmapped ecosystems, understand agricultural and environmental changes, and greatly increase the accuracy and speed of their mapping work. In this blog, we are excited to highlight some of their feedback and showcase the tangible impact of this new technology.

Visualizing the rich details of our world by assigning the colors red, green and blue to three of the 64 dimensions of AlphaEarth Foundations’ embedding fields. In Ecuador, the model sees through persistent cloud cover to detail agricultural plots in various stages of development. Elsewhere, it maps a complex surface in Antarctica—an area notoriously difficult to image due to irregular satellite imaging—in clear detail, and it makes apparent variations in Canadian agricultural land use that are invisible to the naked eye.

Visualizing the rich details of our world by assigning the colors red, green and blue to three of the 64 dimensions of AlphaEarth Foundations’ embedding fields. In Ecuador, the model sees through persistent cloud cover to detail agricultural plots in various stages of development. Elsewhere, it maps a complex surface in Antarctica—an area notoriously difficult to image due to irregular satellite imaging—in clear detail, and it makes apparent variations in Canadian agricultural land use that are invisible to the naked eye.

Visualizing the rich details of our world by assigning the colors red, green and blue to three of the 64 dimensions of AlphaEarth Foundations’ embedding fields. In Ecuador, the model sees through persistent cloud cover to detail agricultural plots in various stages of development. Elsewhere, it maps a complex surface in Antarctica—an area notoriously difficult to image due to irregular satellite imaging—in clear detail, and it makes apparent variations in Canadian agricultural land use that are invisible to the naked eye.

How AlphaEarth Foundations works

AlphaEarth Foundations provides a powerful new lens for understanding our planet by solving two major challenges: data overload and inconsistent information.

First, it combines volumes of information from dozens of different public sources— optical satellite images, radar, 3D laser mapping, climate simulations, and more. It weaves all this information together to analyse the world's land and coastal waters in sharp, 10x10 meter squares, allowing it to track changes over time with remarkable precision.

Second, it makes this data practical to use. The system's key innovation is its ability to create a highly compact summary for each square. These summaries require 16 times less storage space than those produced by other AI systems that we tested and dramatically reduces the cost of planetary-scale analysis.

This breakthrough enables scientists to do something that was impossible until now: create detailed, consistent maps of our world, on-demand. Whether they are monitoring crop health, tracking deforestation, or observing new construction, they no longer have to rely on a single satellite passing overhead. They now have a new kind of foundation for geospatial data.

Diagram showing how AlphaEarth Foundations works, taking non-uniformly sampled frames from a video sequence to index any position in time. This helps the model create a continuous view of the location, while explaining numerous measurements.

To ensure AlphaEarth Foundations was ready for real-world use, we rigorously tested its performance. When compared against both traditional methods and other AI mapping systems, AlphaEarth Foundations was consistently the most accurate. It excelled at a wide range of tasks over different time periods, including identifying land use and estimating surface properties. Crucially, it achieved this in scenarios when label data was scarce. On average, AlphaEarth Foundations had a 24% lower error rate than the models we tested, demonstrating its superior learning efficiency. Learn more in our paper .

Diagram showing a global embedding field broken down into a single embedding, from left to right. Each embedding has 64 components which map to coordinates on a 64-dimensional sphere.

Generating custom maps with the Satellite Embedding dataset

Powered by AlphaEarth Foundations, the Satellite Embedding dataset in Google Earth Engine is one of the largest of its kind with over 1.4 trillion embedding footprints per year. This collection of annual embeddings is already being used by organizations around the world, including the United Nations’ Food and Agriculture Organization , Harvard Forest , Group on Earth Observations , MapBiomas , Oregon State University , the Spatial Informatics Group and Stanford University , to create powerful custom maps that drive real-world insights.

For example, Global Ecosystems Atlas , an initiative aiming to create the first comprehensive resource to map and monitor the world’s ecosystems, is using this dataset to help countries classify unmapped ecosystems into categories like coastal shrublands and hyper-arid deserts . This first of its kind resource will play a critical role in helping countries better prioritize conservation areas, optimize restoration efforts, and combat the loss of biodiversity.

The Satellite Embedding dataset is revolutionizing our work by helping countries map uncharted ecosystems - this is crucial for pinpointing where to focus their conservation efforts.

In Brazil, MapBiomas is testing the dataset to more deeply understand agricultural and environmental changes across the country. This type of map informs conservation strategies and sustainable development initiatives in critical ecosystems like the Amazon rainforest.

As Tasso Azevedo, founder of MapBiomas said, "The Satellite Embedding dataset can transform the way our team works - we now have new options to make maps that are more accurate, precise and fast to produce - something we would have never been able to do before."

Read more about the Satellite Embedding dataset and see tutorials in the Google Earth Engine blog .

Empowering others with AI

AlphaEarth Foundations represents a significant step forward in understanding the state and dynamics of our changing planet. We’re currently using AlphaEarth Foundations to generate annual embeddings and believe they could be even more useful in the future when combined together with general reasoning LLM agents like Gemini. We are continuing to explore the best ways to apply our model's time-based capabilities as part of Google Earth AI , our collection of geospatial models and datasets to help tackle the planet’s most critical needs.

Learn more about AlphaEarth Foundations

Acknowledgements

This work was a collaboration between teams at Google DeepMind and Google Earth Engine.

Christopher Brown, Michal Kazmierski, Valerie Pasquarella, William Rucklidge, Masha Samsikova, Olivia Wiles, Chenhui Zhang, Estefania Lahera, Evan Shelhamer, Simon Ilyushchenko, Noel Gorelick, Lihui Lydia Zhang, Sophia Alj, Emily Schechter, Sean Askay, Oliver Guinan, Rebecca Moore, Alexis Boukouvalas, Pushmeet Kohli