'use strict';

angular.module('scotusChatApp')
  .controller('SpeakerCtrl', function (API, $scope, $rootScope, $stateParams, $http) {
    
   //   //check to see if there is a single speaker
   //  if ($rootScope.speaker){
  	// 	$scope.speaker = $rootScope.speaker;
  	// }
  	// //nope? go get em
  	// else{
   //    $scope.speakerParam = $stateParams.speakerId;
	  //   $http.get('/api/speakers/'+ $stateParams.speakerId).success(function(speaker) {
	  //     $rootScope.speaker = speaker;
	  //     $scope.speaker = speaker;
	  //   });
  	// }

    API.getSpeaker($stateParams.speakerId).then(function(data) {
      $scope.speaker = data;
    }); 

  });
