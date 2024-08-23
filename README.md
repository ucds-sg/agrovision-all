This is a repository of my team's award-winning submission for the Microsoft Azure - United Nations Development Program (UNDP). We were asked to design a system for Singapore's urban farms, which is able to identify weed growth and non-healthy plants and help the farmer to take decisive action before further harm is done.

We built the app with 3 different but equally important components to bring the product together.

1. The 1st component is a small camera drone, supported by Microsoft Azure's IoT platform that flies around the farm on a pre-defined path at regular intervals. The intervals can be decided based on the crop type and farmer's preference.
2. The 2nd component leverages Azure's Compute and Data platforms to store and analyse these photographs from the drone. Leveraging Azure's platform and using Convolution Neural Networks, we were able to achieve high recall rates for identifying weed growth in the farms while maintaining good precision. The former is critical as any weed not rooted out can spread across the farm quite fast and the latter is to improve farmer's efficieny and reduce his workload of having to identify a load of false-positives acorss the farm.
3. The last component that brought the product, 'AgroVision' to life, was a Microsoft PowerBI dashboard, where we leveraged its seamless connection with Azure to disolay insightful and critical information about the farm such as weed-detection locations, crop-failure rates based on plant-type and an ability to connect with adjoining farms to understand whether they are facing similar problems.
