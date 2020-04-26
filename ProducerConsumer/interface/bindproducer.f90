module bindproducer
use iso_c_binding
use bind_data

implicit none

interface

    type(c_ptr) function bind_create_producer(broker) bind(c, name='create_producer')
        use iso_c_binding
        character(kind=c_char), intent(in) :: broker
    end function

    subroutine bind_produce_impl(producer, key, data, datasize, fieldname) bind(c, name='produce')
        use iso_c_binding
        import fKeyMessage
        type(c_ptr), value, intent(in) :: producer
        type(fKeyMessage), intent(in) :: key
        type(c_ptr), value, intent(in) :: data
        integer(c_size_t), intent(in):: datasize
        character(kind=c_char), intent(in) :: fieldname(*)
    end subroutine

end interface

contains 
subroutine bind_produce_3d(producer, field, fieldname, npatches, myrank, datetime, &
    ilonstart, jlatstart, totlonlen, totlatlen,                  &
    longitudeOfFirstGridPoint, longitudeOfLastGridPoint, latitudeOfFirstGridPoint, latitudeOfLastGridPoint)
    use iso_c_binding
    type(c_ptr), value, intent(in) :: producer
    real(c_float), pointer :: field(:,:,:)
    character(kind=c_char, len=32), intent(in) :: fieldname
    integer(c_int), intent(in) :: npatches
    integer(c_int), intent(in) :: myrank
    integer(c_size_t), intent(in) :: datetime
    integer(c_size_t), intent(in) :: ilonstart, jlatstart, totlonlen, totlatlen
    real(c_float), intent(in) :: longitudeOfFirstGridPoint, longitudeOfLastGridPoint, &
            latitudeOfFirstGridPoint, latitudeOfLastGridPoint

    type(fKeyMessage) :: keyMsg
    integer:: k
    integer :: levlen = 1
    integer(kind=c_size_t) :: datasize

    datasize =  size(field,1)*size(field,2)*4

    levlen = size(field,3)

    keyMsg%actionType = 1
    keyMsg%key=fieldname
    keyMsg%npatches = npatches
    keyMsg%myrank=myrank
    keyMsg%datetime=datetime
    keyMsg%ilon_start=ilonstart
    keyMsg%jlat_start=jlatstart
    keyMsg%lev=0
    keyMsg%lonlen=size(field,1)
    keyMsg%latlen=size(field,2)
    keyMsg%levlen=levlen
    keyMsg%totlonlen=totlonlen
    keyMsg%totlatlen=totlatlen
    keyMsg%longitudeOfFirstGridPoint=longitudeOfFirstGridPoint
    keyMsg%longitudeOfLastGridPoint=longitudeOfLastGridPoint
    keyMsg%latitudeOfFirstGridPoint=latitudeOfFirstGridPoint
    keyMsg%latitudeOfLastGridPoint=latitudeOfLastGridPoint
  
    do k=1, size(field,3)
        keyMsg%lev = k-1
        call bind_produce_impl(producer, keyMsg, c_loc(field(:,:,k)), datasize, fieldname)
    enddo 

    end subroutine

    subroutine bind_produce_2d(producer, field, fieldname, npatches, myrank, datetime, &
        ilonstart, jlatstart, totlonlen, totlatlen,                  &
        longitudeOfFirstGridPoint, longitudeOfLastGridPoint, latitudeOfFirstGridPoint, latitudeOfLastGridPoint)
        use iso_c_binding
        type(c_ptr), value, intent(in) :: producer
        real(c_float), pointer :: field(:,:)
        character(kind=c_char, len=32), intent(in) :: fieldname
        integer(c_int), intent(in) :: npatches
        integer(c_int), intent(in) :: myrank
        integer(c_size_t), intent(in) :: datetime
        integer(c_size_t), intent(in) :: ilonstart, jlatstart, totlonlen, totlatlen
        real(c_float), intent(in) :: longitudeOfFirstGridPoint, longitudeOfLastGridPoint, &
                latitudeOfFirstGridPoint, latitudeOfLastGridPoint
    
        type(fKeyMessage) :: keyMsg
        integer :: levlen = 1
        integer(kind=c_size_t) :: datasize

        datasize =  size(field,1)*size(field,2)*4
    

        keyMsg%actionType = 1
        keyMsg%key=fieldname
        keyMsg%npatches = npatches
        keyMsg%myrank=myrank
        keyMsg%datetime=datetime
        keyMsg%ilon_start=ilonstart
        keyMsg%jlat_start=jlatstart
        keyMsg%lev=0
        keyMsg%lonlen=size(field,1)
        keyMsg%latlen=size(field,2)
        keyMsg%levlen=levlen
        keyMsg%totlonlen=totlonlen
        keyMsg%totlatlen=totlatlen
        keyMsg%longitudeOfFirstGridPoint=longitudeOfFirstGridPoint
        keyMsg%longitudeOfLastGridPoint=longitudeOfLastGridPoint
        keyMsg%latitudeOfFirstGridPoint=latitudeOfFirstGridPoint
        keyMsg%latitudeOfLastGridPoint=latitudeOfLastGridPoint
      
        call bind_produce_impl(producer, keyMsg, c_loc(field(:,:)), datasize, fieldname)
    
    end subroutine
    
end