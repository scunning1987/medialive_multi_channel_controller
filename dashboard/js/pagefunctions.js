//
deployment_name = "Disney Streaming"
pipeline = "SINGLE_PIPELINE"
const apiendpointurl = "https://jl66fjfil5.execute-api.us-west-2.amazonaws.com/eng/playout"

const apiendpointurl_global = "https://bg3x65ldw5.execute-api.us-west-2.amazonaws.com/v1/video-deployment-interface"
bucket = "schedule-action-assets"
slate_bucket = "cunsco-east"
startup_slate_key = "SLATE/intro.mp4"
const live_event_map = {
  1:[4856923,"A","us-west-2","https://cunsco-media.s3.us-west-2.amazonaws.com/eml-output/channel1/status.jpg","https://c4af3793bf76b33c.mediapackage.us-west-2.amazonaws.com/out/v1/2869189a30c64f5dbc39e9afa8837ed5/index.m3u8",["s3://cunsco-media/MediaLiveReadyAssets/intro.mp4","s3://mybucket/promo2.mp4","s3://mybucket/promo3.mp4","s3://mybucket/promo4.mp4"]],
  2:[1809084,"B","us-west-2","https://cunsco-media.s3.us-west-2.amazonaws.com/eml-output/channel2/status.jpg","https://10380e91fda5e303.mediapackage.us-west-2.amazonaws.com/out/v1/732ce825d2f64f34908adf94fab71b85/index.m3u8",["","","",""]],
  3:[8466103,"C","us-west-2","https://cunsco-media.s3.us-west-2.amazonaws.com/eml-output/channel3/status.jpg","https://c4af3793bf76b33c.mediapackage.us-west-2.amazonaws.com/out/v1/24875560bc44497882d7a7d3de936517/index.m3u8",["","","",""]],
  4:[790828,"D","us-west-2","https://cunsco-media.s3.us-west-2.amazonaws.com/eml-output/channel4/status.jpg","https://c4af3793bf76b33c.mediapackage.us-west-2.amazonaws.com/out/v1/24875560bc44497882d7a7d3de936517/index.m3u8",["","","",""]],
  5:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  6:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  7:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  8:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  9:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  10:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  11:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  12:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  13:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  14:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  15:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  16:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  17:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  18:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  19:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  20:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  21:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  22:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  23:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  24:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  25:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  26:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  27:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  28:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  29:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  30:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  31:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
  32:[0,"x","region","https://cunsco-media.s3-us-west-2.amazonaws.com/eml-output/placeholder.jpg","",["","","",""]],
}

//// LEAVE CODE BELOW THIS LINE /////

var total_channels = Object.keys(live_event_map).length;
console.log("There are " + total_channels.toString() + " channels in this dashboard")
var thumbnail_size;
if ( parseInt(total_channels) < 9 ) {
  thumbnail_size = 2
} else {
  thumbnail_size = 1
}

var pipSelector = ""
var deployment_name_pretty = deployment_name.toUpperCase().replace("_"," ")

function tableCreate(total_channels){

    var body = document.body,
        tbl  = document.createElement('table'), 
    columns = 8 / thumbnail_size;
    thumb_height = 90 * thumbnail_size; 
    thumb_width = 160 * thumbnail_size;
    tbl.style.width  = '100px';
    tbl.style.padding = '20px';
    rows_required = Math.ceil(total_channels / columns);

    for(var i = 1; i <= rows_required; i++){
        var tr = tbl.insertRow();
        for(var j = 1; j < total_channels + 1; j++){
            if( Math.ceil( j / columns ) == i ){
                var td = tr.insertCell();
                //td.appendChild(document.createTextNode(thumbs[j-1]));
                td.innerHTML = '<img height="'+thumb_height+'" width="'+thumb_width+'" class="thumbs" id="thumb_jpg_'+j.toString()+'" src="'+live_event_map[j][3]+'" onclick=\'thumbclick("'+j.toString()+'")\'></br>'+live_event_map[j][1]
                td.id = "thumb_"+ j.toString()
                //td.style.border = '1px solid black';
                td.style.padding = '10px 10px 10px 10px';
            }
        }
    }
    //document.body.appendChild(tbl)
    document.getElementById("multiviewer").appendChild(tbl);
}


function pageLoadFunction(){
  // write deployment title
  document.getElementById('deployment_title').innerHTML = '<h1 style="text-align:center">'+deployment_name_pretty+'</h1>'

  // create multiviewer PIPs
  tableCreate(total_channels);

  // create video js player element
  document.getElementById('preview_window').innerHTML = '<div id="hlsplayer" class="player2position playerstyle playercolor"><video-js id="my-video" class="vjs-default-skin" controls preload="auto" width="320" height="180"><source src="" type="application/x-mpegURL"></video-js></div>'
}

function thumbclick(channel_number) {
  // set Pip Selector value so it can be used by other functions
  pipSelector = channel_number;
  console.log("PipSelector value is " + pipSelector)
  // add info to channel info section
  document.getElementById("selected_channel_info").innerHTML = '<h3>Channel Info</h3>'
  document.getElementById("selected_channel_info").innerHTML += '<p class="channel_info_text">Channel Number : </br>' + channel_number + '</p>'
  document.getElementById("selected_channel_info").innerHTML += '<p class="channel_info_text"> MediaLive Channel Id: </br>'+live_event_map[channel_number][0]+'</p>'
  document.getElementById("selected_channel_info").innerHTML += '<p class="channel_info_text"> MediaLive Region: </br>'+live_event_map[channel_number][2]+'</p>'
  document.getElementById("selected_channel_info").innerHTML += '<p class="channel_info_text"> Playback Endpoint: </br>'+live_event_map[channel_number][4]+'</p>'
  promos = "</br>"
  live_event_map[channel_number][5].forEach(promo => promos += promo+'</br>')
  document.getElementById("selected_channel_info").innerHTML += '<p class="channel_info_text"> Promos: '+promos+'</p>'


  // re-initialize player with selected channnel
  var myVideo = videojs('my-video');
    myVideo.src([
        {type: "application/x-mpegURL", src: live_event_map[channel_number][4]},
        {type: "rtmp/mp4", src: "rtmp://mycdn"}
    ]);

  // add styling for selected thumbnail
  var channelpips = {...live_event_map}
  delete channelpips[channel_number]

  for ( channel in channelpips ) {
    document.getElementById('thumb_'+channel).classList.add('pips');
    document.getElementById('thumb_'+channel).classList.remove('pipspressed');
    document.getElementById('thumb_'+channel).classList.remove('pipsstream');
  } 
  document.getElementById('thumb_'+pipSelector).classList.remove('pips');
  document.getElementById('thumb_'+pipSelector).classList.add('pipspressed');

  // do API call to get attached live inputs
  getLiveInputs(apiendpointurl)
}

function mediaLiveControl(evt, controlName) {
  var i, tabcontent, tablinks;
  tabcontent = document.getElementsByClassName("tabcontent");
  for (i = 0; i < tabcontent.length; i++) {
    tabcontent[i].style.display = "none";
  }
  tablinks = document.getElementsByClassName("tablinks");
  for (i = 0; i < tablinks.length; i++) {
    tablinks[i].className = tablinks[i].className.replace(" active", "");
  }
  document.getElementById(controlName).style.display = "block";
  evt.currentTarget.className += " active";

  // livestatic vodslate
  if ( controlName == "livestatic" ) {
    if ( pipSelector != "" ) {
      console.log("Selected tab is " + controlName + " need to run function to get available inputs/sources ")
      getLiveInputs(apiendpointurl)
    }
  } else if ( controlName == "vodslate" ) {
    console.log("Selected tab is " + controlName + " need to run function to get available inputs/sources ")
    // s3 api call
    s3getObjectsAPI(bucket, apiendpointurl)
  } else {
    console.log("Selected tab is " + controlName)
  }
}

function chstartstopcontrol(action_type){
  console.log("Running Channel Start/Stop function")
  if ( pipSelector == "" ) {
    console.log("Operator has not selected a channel thumbnail. Select a thumbnail first before an action can be performed")
    alert("Please select a channel thumbnail first!")
  } else {
  document.getElementById(action_type).classList.add('pressedbutton');
  console.log("action type: "+action_type+" for channel ID : "+live_event_map[pipSelector][0])
  // API Call to start/stop channel
  channelStartStop(action_type)

  // reset styling on the pip now that the action has been performed
  document.getElementById("selected_channel_info").innerHTML = ""
  document.getElementById('thumb_'+pipSelector).classList.remove('pipspressed');
  document.getElementById('thumb_'+pipSelector).classList.add('pips');
  fadeAway(action_type)
  // set pipSelector back to empty
  pipSelector = ""
  }
}

function deploymentcontrol(action) {
  console.log("Running deployment control function, selected action is : "+action)
  // placeholder for deployment control api call
  globalStartStopDelete(action)
}
function chliveswitch() {
  console.log("Running Live input switch function")
  if ( pipSelector == "" ) {
    console.log("Operator has not selected a channel thumbnail. Select a thumbnail first before an action can be performed")
    alert("Please select a channel thumbnail first!")
  } else {
  document.getElementById('live').classList.add('pressedbutton');
  input = document.getElementById("live_source_dropdown_select").value
  console.log("Switching to input: "+input+" for channel ID : "+live_event_map[pipSelector][0])
  channelid = live_event_map[pipSelector][0] + ":" + live_event_map[pipSelector][2]
  emlSwitchAction(input, channelid, "", "immediateSwitchLive", "", 200, "master", "immediateswitch")
  }

  // reset styling on the pip now that the action has been performed
  //document.getElementById("selected_channel_info").innerHTML = ""
  document.getElementById('thumb_'+pipSelector).classList.remove('pipspressed');
  document.getElementById('thumb_'+pipSelector).classList.add('pips');
  fadeAway('live')

  // set PipSelector back to empty 
  pipSelector = ""
}

function chvodswitch(){
  console.log("Running VOD input switch function")
  
  if ( pipSelector == "" ) {
    console.log("Operator has not selected a channel thumbnail. Select a thumbnail first before an action can be performed")
    alert("Please select a channel thumbnail first!")
  } else {
  document.getElementById('vod').classList.add('pressedbutton');
  input = document.getElementById("vod_source_dropdown_select").value
  console.log("Switching to input: "+input+" for channel ID : "+live_event_map[pipSelector][0])
  channelid = live_event_map[pipSelector][0] + ":" + live_event_map[pipSelector][2]
  emlSwitchAction(input, channelid, bucket, "immediateSwitch", "", 200, "master", "immediateswitch")
  }

  // reset styling on the pip now that the action has been performed
  //document.getElementById("selected_channel_info").innerHTML = ""
  document.getElementById('thumb_'+pipSelector).classList.remove('pipspressed');
  document.getElementById('thumb_'+pipSelector).classList.add('pips');
  fadeAway('vod')
  // set PipSelector back to empty 
  pipSelector = ""
}

function chpromoins(promo_number){
  console.log("Running promo insert function")

  if ( pipSelector == "" ) {
    console.log("Operator has not selected a channel thumbnail. Select a thumbnail first before an action can be performed")
    alert("Please select a channel thumbnail first!")
  } else {
    console.log("Selected Channel ID : "+live_event_map[pipSelector][0])
    console.log("Found " + live_event_map[pipSelector][5].length + " promos in channnel map")

    if ( promo_number > live_event_map[pipSelector][5].length ) {
      alert("Cannot play promo, it doesn't exist. You need to update the channel map via API with the promo URL")
      
    } else {
    document.getElementById('promo'+promo_number).classList.add('pressedbutton');
    promo_to_play = live_event_map[pipSelector][5][promo_number-1]
    console.log("Sending an API call to MediaLive to start promo : " + promo_to_play)
    s3_url = new URL(promo_to_play.replace("s3://","https://"))
    bucket = s3_url.hostname
    input = s3_url.pathname.replace(/^\/+/, '')
    console.log("Promo bucket : " + bucket)
    console.log("Promo key : " + input)

    channelid = live_event_map[pipSelector][0] + ":" + live_event_map[pipSelector][2]
    console.log("Submitting API Call to insert promo now")
    emlSwitchAction(input, channelid, bucket, "immediateContinue", "", 200, "master", "")
    }
    // reset styling on the pip now that the action has been performed
    document.getElementById("selected_channel_info").innerHTML = ""
    document.getElementById('thumb_'+pipSelector).classList.remove('pipspressed');
    document.getElementById('thumb_'+pipSelector).classList.add('pips');
    fadeAway('promo'+promo_number)
} 
  // set PipSelector back to empty
  pipSelector = ""
} // end chpromoins function


setInterval(function() {
// function to get updated thumbs from MediaLive channels - via S3
for (channel in live_event_map){
  var datevar = Date.now().toString()
  //document.getElementById('thumb_' + channel).innerHTML =  '<img height="90 width="160" class="thumbs" src="'+live_event_map[channel][2]+'?rand='+datevar+'" onclick=\'thumbclick("'+channel.toString()+'")\'>'
  document.getElementById('thumb_jpg_'+channel).src = live_event_map[channel][3]+'?rand='+datevar
}
}, 2000);


var fadeAway = function(buttonid) {
  setTimeout(function(){
  document.getElementById(buttonid).classList.remove('pressedbutton');
 }, 2000);
}

/// API Calls
/// S3 GET OBJECT API CALL - START

function s3getObjectsAPI(bucket, apiendpointurl) {

var param1 = "awsaccount=master";
var param2 = "&functiontorun=s3GetAssetList"
var param3 = "&channelid=0:x";
var param4 = "&maxresults=200";
var param5 = "&bucket="+bucket;
var param6 = "&input=";
var param7 = "&follow=";
var url = apiendpointurl+"?"+param1+param2+param3+param4+param5+param6+param7
console.log("Executing API Call to get S3 assets: " +url )

let dropdown = document.getElementById('vod_source_dropdown_select');
dropdown.length = 0;

let defaultOption = document.createElement('option');
defaultOption.text = 'Choose Asset';

dropdown.add(defaultOption);
dropdown.selectedIndex = 0;

var request = new XMLHttpRequest();
request.open('GET', url, true);

request.onload = function() {
  if (request.status === 200) {
    const data = JSON.parse(request.responseText);
    let option;
    for (let i = 0; i < data.length; i++) {
      option = document.createElement('option');
      option.text = data[i].name;
      option.value = data[i].key;
      dropdown.add(option);
    }
   } else {
    // Reached the server, but it returned an error
  }
}

request.onerror = function() {
  console.error('An error occurred fetching the JSON from ' + url);
};

request.send();
}

/// S3 GET OBJECT API CALL - END
///
/// EML GET ATTACHED INPUTS - START

function getLiveInputs(apiendpointurl) {
var channelid = live_event_map[pipSelector][0] + ":" + live_event_map[pipSelector][2];
var input = document.getElementById("live_source_dropdown_select").value;

var param1 = "awsaccount=master";
var param2 = "&functiontorun=getAttachedInputs"
var param3 = "&channelid="+channelid;
var param4 = "&maxresults=200";
var param5 = "&bucket=";
var param6 = "&input="+input;
var param7 = "&follow=";

var url = apiendpointurl+"?"+param1+param2+param3+param4+param5+param6+param7
console.log("Executing API call to get attached inputs to MediaLive Channel " + channelid )

let dropdown = document.getElementById('live_source_dropdown_select');
dropdown.length = 0;

let defaultOption = document.createElement('option');
defaultOption.text = 'Choose Live Source';

dropdown.add(defaultOption);
dropdown.selectedIndex = 0;

var request = new XMLHttpRequest();
request.open('GET', url, true);

request.onload = function() {
  if (request.status === 200) {
    const data = JSON.parse(request.responseText);
    let option;
    for (let i = 0; i < data.length; i++) {
      option = document.createElement('option');
      option.text = data[i].name;
      option.value = data[i].name;
      dropdown.add(option);
    }
   } else {
    // Reached the server, but it returned an error
  }
}
request.onerror = function() {
  console.error('An error occurred fetching the JSON from ' + url);
};

request.send();
}

/// EML GET ATTACHED INPUTS - END

/// EML SWITCH - START

function emlSwitchAction(file, channelid, bucket, takeType, follow, maxresults, awsaccount, scte){
console.log("Executing API PUT action for switch type "+takeType)

var param1 = "awsaccount="+awsaccount;
var param2 = "&functiontorun="+takeType
var param3 = "&channelid="+channelid;
var param4 = "&maxresults="+maxresults;
var param5 = "&bucket="+bucket;
var param6 = "&input="+file;
var param7 = "&follow="+follow;
var param8 = "&duration="+scte;
var url = apiendpointurl+"?"+param1+param2+param3+param4+param5+param6+param7+param8
console.log("Executing API Call for API switch action : "+url)

var putReq = new XMLHttpRequest();
putReq.open("PUT", url, false);
putReq.setRequestHeader("Accept","*/*");
putReq.send();
}

/// EML SWITCH - END

/// EML SWITCH VOD - START

/// EML SWITCH VOD - END

/// EML CHANNEL START/STOP - START

function channelStartStop(startstop){

if (pipSelector.length < 1){
  alert("Select a channel first...");
  return;
}

channelid = live_event_map[pipSelector][0] + ":" + live_event_map[pipSelector][2];

var param1 = "awsaccount=master";
var param2 = "&functiontorun=channelStartStop"
var param3 = "&channelid="+channelid;
var param4 = "&maxresults=200";
var param5 = "&bucket="+slate_bucket + ":" + startup_slate_key.replace(/\//g,"%2F");
var param6 = "&input="+startstop;
var param7 = "&follow=";
var param8 = "&duration=";
var url = apiendpointurl+"?"+param1+param2+param3+param4+param5+param6+param7+param8
console.log("Executing API Call to Start channnel : " + channelid)

var putReq = new XMLHttpRequest();
putReq.open("PUT", url, false);
putReq.setRequestHeader("Accept","*/*");
putReq.send();

alert("Channel state is changing, please be patient. This may take 60-90 seconds")
}

/// EML CHANNEL START/STOP - END
///
/// GLOBAL START - START

function globalStartStopDelete(task){

var param1 = "name="+deployment_name;
var param2 = "&task="+task;
var url = apiendpointurl_global+"?"+param1+param2
if ( task == "delete" ) {
    console.log("Executing API Call to delete deployment for: " + deployment_name +"\nPlease note this is irreversible")
  } else {
    console.log("Executing API Call to change state to "+task+" for all channels for deployment: " + deployment_name)
  }
var putReq = new XMLHttpRequest();
putReq.open("GET", url, false);
putReq.setRequestHeader("Accept","*/*");
putReq.send();

if ( task == "delete" ) {
    alert("Your deployment is being deleted, you will be notified via email once the purge is complete. All channels will be stopped immediately.")
  } else {
    alert("Channels are in transition state, please be patient. This may take 60-90 seconds")
  }
}


