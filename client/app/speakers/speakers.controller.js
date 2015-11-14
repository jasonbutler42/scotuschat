'use strict';

angular.module('scotusChatApp')
  .controller('SpeakersCtrl', function ($rootScope, $scope, $http, $location) {
    
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

    

});
