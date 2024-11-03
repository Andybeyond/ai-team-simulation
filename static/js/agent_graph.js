document.addEventListener('DOMContentLoaded', function() {
    // Graph data
    const data = {
        nodes: [
            { id: "PM", label: "Project Manager", group: 1 },
            { id: "BA", label: "Business Analyst", group: 2 },
            { id: "DEV", label: "Developer", group: 3 },
            { id: "TEST", label: "Tester", group: 4 },
            { id: "DEVOPS", label: "DevOps", group: 5 },
            { id: "UXD", label: "UX Designer", group: 6 }
        ],
        links: [
            { source: "PM", target: "BA", value: 1, label: "Requirements & Planning" },
            { source: "BA", target: "DEV", value: 1, label: "Technical Specs" },
            { source: "DEV", target: "TEST", value: 1, label: "Implementation" },
            { source: "TEST", target: "DEVOPS", value: 1, label: "Verified Features" },
            { source: "DEVOPS", target: "PM", value: 1, label: "Deployment Status" },
            { source: "PM", target: "DEV", value: 1, label: "Task Assignment" },
            { source: "BA", target: "TEST", value: 1, label: "Test Scenarios" },
            { source: "DEV", target: "DEVOPS", value: 1, label: "Build Artifacts" },
            { source: "UXD", target: "DEV", value: 1, label: "Design Impl." },
            { source: "UXD", target: "TEST", value: 1, label: "UI Testing" },
            { source: "UXD", target: "PM", value: 1, label: "Design Planning" },
            { source: "UXD", target: "BA", value: 1, label: "User Research" }
        ]
    };

    const container = document.querySelector('#agent-graph');
    const width = container.clientWidth;
    const height = 600;
    
    const svg = d3.select('#agent-graph')
        .append('svg')
        .attr('width', '100%')
        .attr('height', height)
        .attr('viewBox', [0, 0, width, height])
        .attr('preserveAspectRatio', 'xMidYMid meet');

    const color = d3.scaleOrdinal()
        .domain([1, 2, 3, 4, 5, 6])
        .range([
            'var(--bs-info)', 
            'var(--bs-purple)', 
            'var(--bs-success)', 
            'var(--bs-warning)', 
            'var(--bs-danger)', 
            'var(--bs-cyan)'
        ]);

    svg.append('defs').selectAll('marker')
        .data(['end'])
        .join('marker')
        .attr('id', 'arrow')
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 25)
        .attr('refY', 0)
        .attr('markerWidth', 8)
        .attr('markerHeight', 8)
        .attr('orient', 'auto')
        .append('path')
        .attr('fill', 'var(--bs-border-color)')
        .attr('d', 'M0,-5L10,0L0,5');

    const simulation = d3.forceSimulation(data.nodes)
        .force('link', d3.forceLink(data.links)
            .id(d => d.id)
            .distance(150))
        .force('charge', d3.forceManyBody()
            .strength(-800))
        .force('center', d3.forceCenter(width / 2, height / 2).strength(0.05))
        .force('collision', d3.forceCollide().radius(60).strength(0.5))
        .force('x', d3.forceX(width / 2).strength(0.02))
        .force('y', d3.forceY(height / 2).strength(0.02));

    const container_g = svg.append('g');

    const link = container_g.append('g')
        .selectAll('path')
        .data(data.links)
        .join('path')
        .attr('class', 'link')
        .attr('marker-end', 'url(#arrow)');

    const linkLabels = container_g.append('g')
        .selectAll('g')
        .data(data.links)
        .join('g')
        .attr('class', 'link-label-group');

    // Create temporary hidden text elements to measure text dimensions
    const tempText = linkLabels.append('text')
        .attr('class', 'link-label')
        .attr('visibility', 'hidden')
        .text(d => d.label);

    // Get text dimensions and create properly sized backgrounds
    tempText.each(function(d) {
        const bbox = this.getBBox();
        const padding = {
            x: bbox.width * 0.2,  // 20% of text width for horizontal padding
            y: bbox.height * 0.3   // 30% of text height for vertical padding
        };
        
        // Store dimensions for use in the actual elements
        d.labelDimensions = {
            width: bbox.width + padding.x,
            height: bbox.height + padding.y,
            padding: padding
        };
    });

    // Remove temporary text elements
    tempText.remove();

    // Create actual label backgrounds with calculated dimensions
    linkLabels.append('rect')
        .attr('class', 'link-label-bg')
        .attr('fill', 'var(--bs-dark)')
        .attr('rx', 4)
        .attr('ry', 4)
        .attr('width', d => d.labelDimensions.width)
        .attr('height', d => d.labelDimensions.height)
        .attr('x', d => -d.labelDimensions.width / 2)
        .attr('y', d => -d.labelDimensions.height / 2);

    // Create actual label text
    linkLabels.append('text')
        .attr('class', 'link-label')
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle')
        .text(d => d.label);

    const node = container_g.append('g')
        .selectAll('g')
        .data(data.nodes)
        .join('g')
        .attr('class', 'node')
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));

    node.append('rect')
        .attr('class', 'label-background')
        .attr('fill', d => color(d.group))
        .attr('rx', 4)
        .attr('ry', 4);

    node.append('text')
        .attr('dy', 4)
        .attr('text-anchor', 'middle')
        .attr('fill', 'var(--bs-light)')
        .attr('font-weight', 'bold')
        .text(d => d.label)
        .each(function(d) {
            const bbox = this.getBBox();
            d3.select(this.parentNode)
                .select('rect.label-background')
                .attr('width', bbox.width + 20)
                .attr('height', bbox.height + 10)
                .attr('x', -bbox.width / 2 - 10)
                .attr('y', -bbox.height / 2 - 5);
        });

    const zoom = d3.zoom()
        .scaleExtent([0.5, 2])
        .on('zoom', (event) => {
            container_g.attr('transform', event.transform);
        });

    svg.call(zoom)
        .call(zoom.transform, d3.zoomIdentity);

    simulation.on('tick', () => {
        // Keep nodes within bounds
        data.nodes.forEach(d => {
            d.x = Math.max(50, Math.min(width - 50, d.x));
            d.y = Math.max(50, Math.min(height - 50, d.y));
        });

        // Update links with straight lines
        link.attr('d', d => `M${d.source.x},${d.source.y}L${d.target.x},${d.target.y}`);

        // Update link labels with improved text orientation
        linkLabels.attr('transform', d => {
            const midX = (d.source.x + d.target.x) / 2;
            const midY = (d.source.y + d.target.y) / 2;
            
            // Calculate angle between source and target
            let angle = Math.atan2(d.target.y - d.source.y, d.target.x - d.source.x) * 180 / Math.PI;
            
            // Adjust angle to ensure text is always readable (not upside down)
            if (angle > 90 || angle < -90) {
                angle += 180;
            }
            
            return `translate(${midX},${midY}) rotate(${angle})`;
        });

        // Update nodes
        node.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.1).restart();
        d.fx = d.x;
        d.fy = d.y;
        d3.select(this).classed('dragging', true);
    }

    function dragged(event, d) {
        d.fx = Math.max(50, Math.min(width - 50, event.x));
        d.fy = Math.max(50, Math.min(height - 50, event.y));
        d3.select(this).classed('dragging', true);
    }

    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = d.x;
        d.fy = d.y;
        d3.select(this).classed('dragging', false);
    }

    window.addEventListener('resize', () => {
        const newWidth = container.clientWidth;
        svg.attr('width', newWidth);
        svg.attr('viewBox', [0, 0, newWidth, height]);
        simulation.force('center', d3.forceCenter(newWidth / 2, height / 2).strength(0.05))
            .alpha(0.3)
            .restart();
    });
});
