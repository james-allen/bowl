var shapeGenerator = function(shape) {
    var coords = [];
    var interpolate;
    switch (shape) {
    case "square":
        coords = [
            {x: -0.5, y: -0.5},
            {x: -0.5, y: 0.5},
            {x: 0.5, y: 0.5},
            {x: 0.5, y: -0.5},
            {x: -0.5, y: -0.5}
        ];
        interpolate = "linear";
        break;
    case "circle":
        var nPoint = 50;
        var theta;
        for (var i = 0; i <= nPoint; i++) {
            theta = 2 * Math.PI * i / nPoint;
            coords[i] = {x: 0.5*Math.cos(theta), y: 0.5*Math.sin(theta)};
        }
        interpolate = "basis";
        break;
    case "rising":
        coords = [
            {x: -0.5, y: 0.5},
            {x: -0.5, y: 0},
            {x: 0, y: -0.5},
            {x: 0.5, y: -0.5},
            {x: 0.5, y: 0},
            {x: 0, y: 0.5},
            {x: -0.5, y: 0.5}
        ];
        interpolate = "linear";
        break;
    case "rectangleHorizontal":
        coords = [
            {x: -0.5, y: -0.35},
            {x: -0.5, y: 0.35},
            {x: 0.5, y: 0.35},
            {x: 0.5, y: -0.35},
            {x: -0.5, y: -0.35}
        ];
        interpolate = "linear";
        break;
    case "diamond":
        coords = [
            {x: -0.5, y: 0},
            {x: 0, y: 0.5},
            {x: 0.5, y: 0},
            {x: 0, y: -0.5},
            {x: -0.5, y: 0}
        ];
        interpolate = "linear";
        break;
    case "chevron":
        coords = [
            {x: -0.5, y: 0.5},
            {x: -0.5, y: -0.25},
            {x: 0, y: -0.5},
            {x: 0.5, y: -0.25},
            {x: 0.5, y: 0.5},
            {x: 0, y: 0.25},
            {x: -0.5, y: 0.5}
        ];
        interpolate = "linear";
        break;
    }
    return {coordinates: coords, interpolate: interpolate};
}

var createShape = function(shape, x0, y0, diameter, parent, class_, id) {
    var shapeData = shapeGenerator(shape);
    var coords = shapeData.coordinates;
    for (var i = 0; i < coords.length; i++) {
        coords[i].x = coords[i].x * diameter + x0;
        coords[i].y = coords[i].y * diameter + y0;
    }
    var line = d3.svg.line()
        .x(function(d) {return d.x;})
        .y(function(d) {return d.y;})
        .interpolate(shapeData.interpolate);
    var symbol = parent.append("path")
        .attr("class", class_)
        .attr("id", id)
        .data([coords])
        .attr("d", line);
    return shapeData.interpolate;
}

var moveShape = function(id, deltaX, deltaY, interpolate) {
    var path = d3.select("#"+id);
    var data = path.data()[0];
    for (var i = 0; i < data.length; i++) {
        data[i].x += deltaX;
        data[i].y += deltaY;
    }
    var line = d3.svg.line()
        .x(function(d) { return d.x; })
        .y(function(d) { return d.y; })
        .interpolate(interpolate);
    return path.transition().attr("d", line);
}

var drawPlayer = function(player, parent) {
    var x0 = viewData.margin + (player.xpos+0.5)*viewData.squareSize;
    var y0 = viewData.margin + (player.ypos+0.5)*viewData.squareSize;
    var g = parent.append("g")
        .attr("class", player.side)
        .classed("player", true)
        .classed("selected", false)
        .attr("id", playerId(player))
        .on("click", function(){clickPlayer(player);})
        .on("mouseover", function(){updateInfoBox("infoBoxHighlighted", player);highlightStep(player);})
        .on("mouseout", function(){updateInfoBox("infoBoxHighlighted", null);});
    player.interpolate = createShape(
        shapeSelector(player), x0, y0, viewData.playerSize, g, "playerSymbol", 
        playerId(player)+"Symbol");
    g.append("text")
        .attr("x", x0)
        .attr("y", y0)
        .attr("class", "playerNumber")
        .attr("id", playerId(player)+"Number")
        .text(player.num);
}

var shapeSelector = function(player) {
    return shapeDatabase[player.race][player.position];
}

var shapeDatabase = {
    "human": {
        "Lineman": "circle",
        "Thrower": "rising",
        "Catcher": "diamond",
        "Blitzer": "chevron",
    },
    "ogre": {
        "Ogre": "square"
    },
    "orc": {
        "Lineman": "circle",
        "Thrower": "rising",
        "Black Orc Blocker": "rectangleHorizontal",
        "Blitzer": "chevron"
    }
}
