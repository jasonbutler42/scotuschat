'use strict';

angular.module('scotusChatApp')
  .controller('ChatCtrl', function (API, $scope, $stateParams) {

  	var speakers = [];
  	var loaded = false;
    
    API.getChat($stateParams.chatId).then(function(data) {
      $scope.chat = data;
      loaded = true;
    }); 


    $scope.getSpeaker = function(speakerTag, speakerList) {
    	console.log('looking for ', speakerTag, ' in ',speakerList);
    	var speaker = null;
   //  	$scope.speakers.forEach(function(i,v) {
			// if (speakerTag === v.tag) {
			// 	speaker = v; 
			// }
   //  	});
    	return speaker;
    };

  });
