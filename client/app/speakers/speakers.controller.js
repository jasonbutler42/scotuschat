'use strict';

angular.module('scotusChatApp')
  .controller('SpeakersCtrl', function ($rootScope, $scope, $http, $location, $stateParams) {
    
  	//check to see if there are a list of speakers
  	if ($rootScope.speakers){
  		$scope.speakers = $rootScope.speakers;
  	}
  	//nope? ok go get em.
  	else{
	    $http.get('/api/speakers/').success(function(speakers) {
	      $rootScope.speakers = speakers;
	      $scope.speakers = speakers;
	    });
  	}

    $scope.goTo = function(speaker){
    	$rootScope.speaker = speaker;
    	$location.path('/speakers/speaker/'+ speaker._id);
    };

    //check to see if there is a single speaker
    if ($rootScope.speaker){
  		$scope.speaker = $rootScope.speaker;
  	}
  	//nope? go get em
  	else{;
      $scope.speakerParam = $stateParams.speakerId;
	    $http.get('/api/speakers/'+ $scope.speakerParam).success(function(speaker) {
	      $rootScope.speaker = speaker;
	      $scope.speaker = speaker;
	    });
  	}

    

});
