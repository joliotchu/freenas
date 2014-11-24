/** @jsx React.DOM */

// Dashboard
// =========
// Default view for FreeNAS, shows overview of system and other general
// information.

"use strict";


var React = require("react");

var Widget   = require("../components/Widget");

var Dashboard = React.createClass({
  componentDidMount: function() {
  },

  render: function() {
    return (
      <div>
        <h2>Dashboard View</h2>
        <div ref="widgetAreaRef" className="widgetArea">
        <Widget positionX="15" positionY="150" title="Widget" size="large" content="/img/lg_widget.png" />
        <Widget positionX="510" positionY="150" title="Widget" size="medium" content="/img/md_widget.png" />
        <Widget positionX="510" positionY="480" title="Widget" size="small" content="/img/sm_widget.png" />
        <Widget positionX="675" positionY="480" title="Widget" size="small" content="/img/sm_widget.png" />
        <Widget positionX="15" positionY="645" title="Widget" size="large" content="/img/lg_widget.png" />
        <Widget positionX="840" positionY="150" title="Widget" size="medium" content="/img/md_widget.png" />
        <Widget positionX="840" positionY="480" title="Widget" size="medium" content="/img/md_widget.png" />
        <Widget positionX="1170" positionY="150" title="Widget" size="small" content="/img/sm_widget.png" />
        <Widget positionX="1170" positionY="315" title="Widget" size="small" content="/img/sm_widget.png" />
        <Widget positionX="510" positionY="645" title="Widget" size="longsmall" content="/img/sm_widget.png" />
        <Widget positionX="1170" positionY="480" title="Widget" size="heightsmall" content="/img/sm_widget.png" />
        </div>
      </div>
    );
  }
});

module.exports = Dashboard;